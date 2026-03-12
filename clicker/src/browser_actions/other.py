import sys

sys.path.append('.')

import asyncio
import json
import re
from collections import defaultdict
from urllib.parse import parse_qs

from playwright.async_api import BrowserContext

from agent.schemas import AgentState
from browser_actions.user_storage import UserStorage
from core.schemas import ApiStep, CaseStatusEnum


def is_empty_payload(value) -> bool:
    if value is None:
        return True
    if isinstance(value, (dict, list)) and not value:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


async def execute_api_request(
    context: BrowserContext,
    request_raw: ApiStep,
    timeout: float = 60000,  # 1 минута по дефолту
    ignore_https_errors: bool = True,
    max_redirects: int = 20,
    max_retries: int = 0
) -> dict:
    """
    Выполняет API запрос на основе curl команды.

    Args:
        context: контекст браузера
        request_raw: распарсенный curl
        timeout: таймаут запроса в миллисекундах
        ignore_https_errors: игнорировать ошибки HTTPS
        max_redirects: максимальное количество редиректов
        max_retries: максимальное количество повторных попыток при ошибках сети

    Returns:
        Словарь с результатами запроса:
        {
            "status": int,  # HTTP статус код
            "status_text": str,
            "ok": bool,
            "text": str,  # Текст ответа
            "headers": dict,  # Заголовки ответа
            "url": str  # Финальный URL после редиректов
        }
    """

    api_request_context = context.request

    request_params = {
        "url": request_raw.url,
        "headers": request_raw.headers or {},
        "timeout": timeout,
        "max_redirects": max_redirects,
        "max_retries": max_retries,
        "ignore_https_errors": ignore_https_errors
    }

    # данные запроса
    if not is_empty_payload(request_raw.data):
        content_type = request_raw.get_content_type()

        if not content_type or 'application/json' in content_type:

            if isinstance(request_raw.data, (dict, list)):
                # dict/list → Playwright сам сериализует, можно отдать как есть
                request_params["data"] = request_raw.data
            elif isinstance(request_raw.data, str):
                # строку оставляем как есть
                request_params["data"] = request_raw.data
            else:
                request_params["data"] = json.dumps(request_raw.data)

        elif 'application/x-www-form-urlencoded' in content_type and isinstance(request_raw.data, str):
            parsed_data = parse_qs(request_raw.data)
            form_data = {k: v[0] if len(v) == 1 else v for k, v in parsed_data.items()}
            request_params["form"] = form_data
        elif 'application/x-www-form-urlencoded' in content_type and isinstance(request_raw.data, dict):
            request_params["form"] = request_raw.data
        else:
            request_params["data"] = request_raw.data

    # Файлы
    if request_raw.files:
        request_params["multipart"] = request_raw.files

    method = request_raw.method.lower()

    if method == "get":
        response = await api_request_context.get(**request_params)
    elif method == "post":
        response = await api_request_context.post(**request_params)
    elif method == "put":
        response = await api_request_context.put(**request_params)
    elif method == "patch":
        response = await api_request_context.patch(**request_params)
    elif method == "delete":
        response = await api_request_context.delete(**request_params)
    elif method == "head":
        response = await api_request_context.head(**request_params)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")

    # Получаем текст ответа
    response_text = await response.text()
    try:
        response_json = await response.json()
        json_ok = True
    except Exception:
        # response_json = None
        response_json = response_text[:1000]
        json_ok = False

    return {
        "status": response.status,
        "status_text": response.status_text,
        "ok": response.ok,
        "text": response_text,
        "json": response_json,
        "json_ok": json_ok,
        "headers": dict(response.headers),
        "url": response.url
    }


def resolve_key_path(container, key_path):
    """
    Возвращает (parent, last_key, current_value) по key_path.
    Поддерживает data.user.contacts[0].value
    """
    parts = re.split(r'\.(?![^\[]*\])', key_path)  # делим по ".", но не внутри [..]
    current = container
    parent = None
    last_key = None

    for part in parts:
        # индексированный доступ: key[0]
        m = re.match(r'(\w+)\[(\d+)\]$', part)
        if m:
            key, idx = m.group(1), int(m.group(2))
            parent = current[key]
            current = parent[idx]
            last_key = idx
        else:
            parent = current
            current = parent[part]
            last_key = part

    return parent, last_key, current


def replace_with_positions(text: str, variables: list, user_storage) -> str:
    """
    Заменяет все переменные внутри одной строки text по positions.
    variables: список var_info для одного key
    """
    # сортируем по стартовой позиции, чтобы шло слева направо
    variables_sorted = sorted(variables, key=lambda v: v["positions"][0][0])
    offset = 0
    updated_text = text

    for var_info in variables_sorted:
        var_name = var_info.get("name")
        positions = var_info.get("positions", [])
        if not positions:
            continue

        var_value = user_storage.get_value(var_name)
        if var_value is None:
            continue

        start, end = positions[0]
        start -= offset
        end -= offset

        old_value = updated_text[start:end]
        updated_text = updated_text[:start] + str(var_value) + updated_text[end:]

        # пересчитываем сдвиг
        diff = len(old_value) - len(str(var_value))
        offset += diff

        # обновляем позиции
        new_end = start + len(str(var_value))
        var_info["positions"] = [[start, new_end]]
        var_info["value"] = var_value

    return updated_text


def extract_jsonpath_value(template: str, response: dict, state: AgentState):
    """
    Извлекает значение из response по JSONPath-подобному пути.
    """
    current = None
    parts = template.split(".")
    try:
        # JSONPath (response.body.xxx или response.body[0].xxx или response.body[0].users[1].name)
        if len(parts) > 0 and parts[0] == "response":

            path_parts = []

            # Разбираем путь ('body[0]' -> 'body', '[0]')
            for part in parts[1:]:
                # Разделяем часть на компоненты ('role_title2[1][0]' -> ['role_title2', '[1]', '[0]'])
                components = []
                remaining = part
                while remaining:
                    # Ищем первый [
                    bracket_pos = remaining.find('[')
                    if bracket_pos == -1:
                        components.append(remaining)
                        break

                    # Добавляем часть до [
                    if bracket_pos > 0:
                        components.append(remaining[:bracket_pos])

                    # Ищем закрывающую ]
                    close_pos = remaining.find(']', bracket_pos)
                    if close_pos == -1:
                        raise ValueError(f"Invalid array index in path: {remaining}")

                    # Добавляем индекс
                    components.append(remaining[bracket_pos:close_pos + 1])
                    remaining = remaining[close_pos + 1:]

                path_parts.extend(components)

            # Начинаем с response
            if not path_parts:
                raise ValueError(f"Empty path in template: {template}")

            # Определяем начальную точку (body, headers, statusCode и т.д.)
            first_part = path_parts[0]

            if first_part == "body":
                if not response["json_ok"]:
                    raise ValueError(f"No JSON body in response for {template}")
                current = response["json"]
                path_parts = path_parts[1:]

            elif first_part == "statusCode":
                current = str(response["status"])
                path_parts = path_parts[1:]

            elif first_part == "text":
                current = response["text"]
                path_parts = path_parts[1:]

            elif first_part == "headers":
                current = response.get("headers", {})
                path_parts = path_parts[1:]

            elif first_part in response:
                current = response[first_part]
                path_parts = path_parts[1:]

            else:
                raise ValueError(f"Unknown response property: {first_part}")

            # Обрабатываем оставшийся путь
            for component in path_parts:
                if current is None:
                    raise ValueError(f"Path {template}: cannot access property of null at {component}")

                # Обработка индекса листа [n]
                if component.startswith('[') and component.endswith(']'):
                    idx = component[1:-1]
                    if not idx.isdigit():
                        raise ValueError(f"Path {template}: invalid array index {component}")
                    idx = int(idx)

                    if not isinstance(current, (list, tuple)):
                        raise ValueError(f"Path {template}: expected array at {component}")
                    if idx >= len(current):
                        raise ValueError(f"Path {template}: index {idx} out of bounds")
                    current = current[idx]
                # Обработка ключа дикта
                else:
                    if not isinstance(current, dict):
                        raise ValueError(f"Path {template}: expected object at {component}")
                    if component not in current:
                        raise ValueError(f"Path {template}: missing property {component}")
                    current = current[component]

            return current

    except (IndexError, KeyError, ValueError) as e:
        state.logger.error(f"Failed to resolve {template}: {str(e)}")
        # state.user_storage.set(var_name, "undefined")
        raise e
    except Exception as e:
        state.logger.error(f"Unexpected error processing {template}: {str(e)}")
        # state.user_storage.set(var_name, "error")
        raise e


async def process_variables_before_plain_step(state: AgentState):
    """
    ставим переменные в обычных степах
    """
    if state.step_state.action == 'API':
        return

    def clone_variables(variables_info: list) -> list:
        cloned = []
        for var_info in variables_info:
            if not isinstance(var_info, dict):
                continue
            var_copy = dict(var_info)
            positions = var_info.get("positions", [])
            if isinstance(positions, list):
                var_copy["positions"] = [pos[:] if isinstance(pos, list) else pos for pos in positions]
            cloned.append(var_copy)
        return cloned

    def apply_variables_to_container(container: dict, variables_info: list):
        def set_value(target, key, value):
            if isinstance(target, dict):
                target[key] = value
                return
            if isinstance(target, list) and isinstance(key, int):
                target[key] = value
                return

            # Pydantic-like модели (например StepPayload / DictLikeModel)
            if isinstance(key, str):
                if hasattr(target, key):
                    setattr(target, key, value)
                    return
                model_extra = getattr(target, "model_extra", None)
                if isinstance(model_extra, dict):
                    model_extra[key] = value
                    return

            # fallback для иных mapping-like объектов
            if hasattr(target, "__setitem__"):
                target[key] = value

        vars_by_key = defaultdict(list)
        for var_info in variables_info:
            if not isinstance(var_info, dict):
                continue
            key_path = var_info.get("key")
            if key_path:
                vars_by_key[key_path].append(var_info)

        for key_path, vars_group in vars_by_key.items():
            try:
                parent, last_key, current_value = resolve_key_path(container, key_path)
            except Exception:
                continue

            if not isinstance(current_value, str):
                continue

            new_value = replace_with_positions(current_value, vars_group, state.user_storage)
            set_value(parent, last_key, new_value)

            if container is state.step_state.current_step and isinstance(last_key, str):
                if hasattr(state.step_state, last_key):
                    setattr(state.step_state, last_key, new_value)

                if isinstance(state.step_state.extra, dict) and last_key in ("value", "method", "url"):
                    state.step_state.extra[last_key] = new_value

    # Обрабатываем переменные в экшен плане степа (current_step)
    step_extra = state.step_state.extra if isinstance(state.step_state.extra, dict) else None
    if step_extra and isinstance(step_extra.get("variables"), list):
        apply_variables_to_container(
            state.step_state.current_step,
            step_extra["variables"]
        )

    # Обрабатываем переменные из основного шага и применяем их к current_step и case_steps
    step_data = state.case_steps[state.current_step_index]
    if isinstance(step_data, dict) and "extra" in step_data and "variables" in step_data["extra"]:
        variables_info = step_data["extra"]["variables"]
        if isinstance(variables_info, list):
            apply_variables_to_container(
                state.step_state.current_step,
                clone_variables(variables_info)
            )
            apply_variables_to_container(step_data, variables_info)

    # Устанавливаем обновленное значение в extra экшен плана
    new_value_step_description = step_data.get("value") if isinstance(step_data, dict) else step_data

    if isinstance(state.step_state.extra, dict):
        state.step_state.extra["value"] = new_value_step_description

    # state.logger.info(f"новый экшен план {state.step_state}")
    # state.logger.info(f"новый степ {state.case_steps[state.current_step_index]}")


async def process_variables_before_request(state: AgentState):
    """
    Пишем в user_storage из set_variables
    Заменяем variables из user_storage
    с пересчетом актуальных позиций

    "action_plan": [
            {
                "action_type": "API",
                "value": "curl -X POST -d \"param1=USER!\" https://postman-echo.com/post",
                "extra": {
                    "set_variables": {
                        "login": "123"
                    },
                    "variables": [
                        {
                            "name": "login",
                            "value": "USER!",
                            "original": "{{login}}",
                            "positions": [
                                [
                                    24,
                                    29
                                ]
                            ],
                            "key": "value"
                        }
                    ]
                }
            },
    """
    if not state.step_state.extra:
        return

    # Обновляем variables
    if "variables" not in state.step_state.extra:
        return

    variables_info = state.step_state.extra["variables"]
    if not isinstance(variables_info, list):
        return

    def set_value(target, key, value):
        if isinstance(target, dict):
            target[key] = value
            return
        if isinstance(target, list) and isinstance(key, int):
            target[key] = value
            return

        if isinstance(key, str):
            if hasattr(target, key):
                setattr(target, key, value)
                return
            model_extra = getattr(target, "model_extra", None)
            if isinstance(model_extra, dict):
                model_extra[key] = value
                return

        if hasattr(target, "__setitem__"):
            target[key] = value

    # сгруппировать по key
    vars_by_key = defaultdict(list)
    for var_info in variables_info:
        key_path = var_info.get("key")
        if key_path:
            vars_by_key[key_path].append(var_info)

    for key_path, vars_group in vars_by_key.items():
        parent, last_key, current_value = resolve_key_path(state.step_state.current_step, key_path)
        if isinstance(current_value, str):
            new_value = replace_with_positions(current_value, vars_group, state.user_storage)

            set_value(parent, last_key, new_value)
            # state.step_state.extra[last_key] = new_value
            if last_key in ("value", "method", "url") and parent is state.step_state.current_step:
                # только верхний уровень
                state.step_state.extra[last_key] = new_value


async def process_variables_after_response(state: AgentState, response: dict):
    """
    Ставим переменные из JSONPath из ответа запроса
    - response.body[0].role_title
    - response.body[0].role_title2[1][0]
    - response.body.role_title
    - response.headers.content-type
    - response.statusCode
    """

    if not state.step_state.extra or "set_variables" not in state.step_state.extra:
        return

    set_vars = state.step_state.extra["set_variables"]
    if not isinstance(set_vars, dict):
        return

    state.step_state.extra.setdefault("variables_store", {})

    # Сохраняем статику из set_variables для следующих шагов
    if isinstance(set_vars, dict):
        for var_name, var_value in set_vars.items():
            if isinstance(var_value, str) and not (var_value.startswith("{{") and var_value.endswith("}}")):
                state.user_storage.set(var_name, var_value)
                state.step_state.extra["variables_store"][var_name] = var_value

    for var_name, var_value in set_vars.items():
        if not isinstance(var_value, str):
            continue

        if not var_value.startswith("{{response.") or not var_value.endswith("}}"):
            continue

        template = var_value[2:-2]  # извлекаем из фигурок'response.xxx.yyy'

        current = extract_jsonpath_value(template, response, state)
        # ставим значение
        if current is None:
            state.user_storage.set(var_name, "null")
            state.step_state.extra["variables_store"][var_name] = "null"
            state.logger.info(f"state.user_storage.set: {var_name}=null")
        elif isinstance(current, (list, dict)):
            current_json = json.dumps(current)
            state.user_storage.set(var_name, current_json)
            state.step_state.extra["variables_store"][var_name] = current_json
            state.logger.info(f"state.user_storage.set: {var_name}={current}")
        else:
            state.user_storage.set(var_name, str(current))
            state.step_state.extra["variables_store"][var_name] = str(current)
            state.logger.info(f"state.user_storage.set: {var_name}={current}")


async def validate_response(state: AgentState, response: dict):
    """
    Валидирует ответ API на основе правил в validations.
    """
    if not state.step_state.extra or "validations" not in state.step_state.extra:
        return

    validations = state.step_state.extra["validations"]
    if not isinstance(validations, list):
        return

    state.step_state.extra.setdefault("validations_log", [])

    for validation in validations:
        if not isinstance(validation, dict):
            continue

        # Извлекаем параметры валидации
        target = validation.get("target", "")
        validation_type = validation.get("validation_type", "")
        expected_value = validation.get("expected_value", "")

        if not target or not validation_type:
            continue

        # Получаем фактическое значение
        if target.startswith("{{response.") and target.endswith("}}"):
            # JSONPath из response
            actual_value = extract_jsonpath_value(target[2:-2], response, state)

            if actual_value is None:
                actual_value = "null"
            elif isinstance(actual_value, (list, dict)):
                actual_value = json.dumps(actual_value)
            else:
                actual_value = str(actual_value)

        elif target.startswith("{{") and target.endswith("}}"):
            # Переменная из user_storage
            var_name = target[2:-2]
            actual_value = state.user_storage.get_value(var_name, strict=True)
            if actual_value is None:
                raise ValueError(f"Variable '{var_name}' not found in storage")
        else:
            # Просто константа
            actual_value = target

        # state.logger.info(f"validations: {target=}={actual_value}")

        # Получаем ожидаемое значение из стора, или остается как есть (константа)
        if isinstance(expected_value, str) and expected_value.startswith("{{") and expected_value.endswith("}}"):
            # Переменная из user_storage
            var_name = expected_value[2:-2]
            expected_value = state.user_storage.get_value(var_name, strict=True)
            if expected_value is None:
                raise ValueError(f"Variable '{var_name}' not found in storage")

        # Приводим к строке для сравнения
        actual_str = str(actual_value) if actual_value is not None else "null"
        expected_str = str(expected_value) if expected_value is not None else "null"

        # Выполняем проверку
        is_valid = False
        if validation_type == "=":
            is_valid = actual_str == expected_str
        elif validation_type == "!=":
            is_valid = actual_str != expected_str
        elif validation_type == ">":
            is_valid = float(actual_str) > float(expected_str)
        elif validation_type == "<":
            is_valid = float(actual_str) < float(expected_str)
        elif validation_type == ">=":
            is_valid = float(actual_str) >= float(expected_str)
        elif validation_type == "<=":
            is_valid = float(actual_str) <= float(expected_str)
        elif validation_type == "IN":
            expected_list = [x.strip() for x in expected_str.split(",")]
            is_valid = actual_str in expected_list
        elif validation_type == "NOT IN":
            expected_list = [x.strip() for x in expected_str.split(",")]
            is_valid = actual_str not in expected_list
        elif validation_type == "LIKE":
            is_valid = expected_str in actual_str
        else:
            raise ValueError(f"Unknown validation type: {validation_type}")

        if not is_valid:
            error_msg = (
                f"Validation failed: {target} {validation_type} {expected_value}\n"
                f"Actual value: {actual_str}"
            )
            state.step_state.extra["validations_log"].append(error_msg)
            raise ValueError(error_msg)
        msg = f"validation success: {target=} {validation_type=} {expected_value=} | {actual_str=}"
        state.logger.info(msg)
        state.step_state.extra["validations_log"].append(msg)


async def main():
    import logging
    import time
    import uuid
    from datetime import datetime, timezone
    from io import StringIO
    from pathlib import Path

    from agent.schemas import AgentState, StepState

    run_id = str(uuid.uuid4())

    action_plan = [{
        "action_type": "API",
        "value": "curl -X GET https://api.example.com/api/workspace/get_list_user_workspaces -H \"accept: application/json\" -H \"Authorization: Bearer {{token}}\"",
        "extra": {
            "set_variables": {
                "example1": "{{response.body[0].role_title2[1][1].test}}",
                "example2": "{{response.headers.server}}",
                "example3": "{{response.headers}}",
                "example4": "{{response.body}}",
                "example5": "{{response.statusCode}}",
                "example6": "{{response.text}}",
                "example7": "{{response.url}}",
                # "example8": "{{response.notfound}}"
            },
            "validations": [{"target": "{{response.body[0].role_title2[1][1].test}}", "validation_type": "=", "expected_value": "123"},
                            {"target": "{{example1}}", "validation_type": "=", "expected_value": "123"},
                            {"target": "123", "validation_type": "=", "expected_value": "123"},
                            {"target": "{{example1}}", "validation_type": "!=", "expected_value": "1234"},
                            {"target": "{{example1}}", "validation_type": "LIKE", "expected_value": "12"},
                            {"target": "{{response.body[0].role_title2[1][1].test}}", "validation_type": "=", "expected_value": "{{example1}}"},
                            {"target": "{{response.body[0].role_title2[1][1].test}}", "validation_type": "IN", "expected_value": "123,456,789"},
                            {"target": "{{response.body[0].role_title2[1][1].test}}", "validation_type": "NOT IN", "expected_value": "456,789"},
                            {"target": "{{response.url}}", "validation_type": "LIKE", "expected_value": "url"},
                            {"target": "{{example7}}", "validation_type": "=", "expected_value": "{{example7}}"},
                            {"target": "{{response.headers.server}}", "validation_type": "=", "expected_value": "uvicorn"},
                            {"target": "{{example2}}", "validation_type": "!=", "expected_value": "{{example7}}"},]
        }
    }]
    headers = {"content-length": 3489,
               "content-type": "application/json",
               "date": "Fri,15 Aug 2025 07:20:56 GMT",
               "server": "uvicorn",
               "x-request-id": "a29f9269-827e-4325-805e-488e26dfe14d"}

    response_json = [{"workspace_id": "a664d82f-7ab0-4170-b995-2e6c4e320012",
                      "workspace_name": "user@example.com",
                      "owner": "e014a858-cb79-4120-8a38-ba982ddcd862",
                      "role": "admin",
                      "role_title": "QA Manager",
                      "role_title2": [1, [7, {"test": 123}], 3, 5]}]
    response = {"status": 200,
                "status_text": "response.status_text",
                "ok": "response.ok",
                "text": "response_text",
                "json": response_json,
                "headers": headers,
                "url": "response.url"
                }

    logger = logging.getLogger(str(uuid.uuid4()))
    log_buffer = StringIO()
    log_handler = logging.StreamHandler(log_buffer)
    formatter = logging.Formatter('%(asctime)s (%(filename)s:%(funcName)s:%(lineno)d) [%(levelname)s] - %(message)s')
    log_handler.setFormatter(formatter)
    logger.addHandler(log_handler)
    logger.setLevel(logging.INFO)

    state = AgentState(browser=None,
                       context=None,
                       session=None,
                       tab_manager=None,
                       user_storage=UserStorage(),
                       page=None,
                       logger=logger,
                       log_buffer=log_buffer,
                       log_handler=log_handler,
                       action_plan=action_plan,
                       steps_descriptions=[],
                       screenshot_base_path=Path("screenshots") / run_id,
                       trace_file_path=f"{run_id}_trace.zip",
                       run_id=run_id,
                       case_id="",
                       case_name="",
                       inference_client=None,
                       reflection_client=None,
                       start_dt=datetime.now(timezone.utc),
                       width=1920,
                       height=1080,
                       status=CaseStatusEnum.FAILED,
                       run_summary="Error during execution",
                       local_async_engine=None,
                       background_video_generate=True)

    current_step = state.action_plan[state.current_step_index]
    step_id = f"{state.current_step_index}_{state.current_attempt}"
    step_state = StepState(
        step_id=step_id,
        current_step=current_step,
        action=current_step['action_type'],
        element_description=current_step.get('element_description', None),
        container_description=current_step.get('container_description', None),
        before_screenshot_path=state.screenshot_base_path / \
            f'screenshot_{step_id}_before.jpeg',
        annotated_screenshot_path=state.screenshot_base_path / \
            f'screenshot_{step_id}_annotated.jpeg',
        after_screenshot_path=state.screenshot_base_path / \
            f'screenshot_{step_id}_after.jpeg',
        full_screenshot_path=state.screenshot_base_path / \
            f'screenshot_{step_id}_full.jpeg',
        start_time=time.time(),
        text_to_type=current_step.get('text_to_type', None),
        wait_time=int(current_step.get('wait_time', 30)),
        key_to_press=current_step.get('key_to_press', None),
        tab_name=current_step.get('tab_name', None),
        extra=current_step.get('extra', None),
    )
    state.step_state = step_state
    state.status = CaseStatusEnum.PASSED

    await process_variables_after_response(state, response)
    state.logger.info("-" * 60)
    await validate_response(state, response)

if __name__ == "__main__":
    asyncio.run(main())
