import anthropic
import base64
import json
from typing import Dict, List, Tuple

# Определение кастомного tool для клика
CLICK_TOOL = {
    "name": "click_coordinates",
    "description": """Инструмент для определения координат клика на изображении экрана.
    Используй этот tool когда нужно кликнуть по элементу на скриншоте.
    Координаты должны быть в пикселях относительно левого верхнего угла изображения.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "x": {
                "type": "number",
                "description": "Координата X (горизонтальная позиция) в пикселях от левого края изображения"
            },
            "y": {
                "type": "number",
                "description": "Координата Y (вертикальная позиция) в пикселях от верхнего края изображения"
            },
            "element_description": {
                "type": "string",
                "description": "Описание элемента, по которому выполняется клик (например: 'кнопка Login', 'поле ввода email')"
            },
            "confidence": {
                "type": "string",
                "enum": ["high", "medium", "low"],
                "description": "Уверенность в правильности определения координат"
            }
        },
        "required": ["x", "y", "element_description", "confidence"]
    }
}

SYSTEM_PROMPT = """Ты - эксперт по анализу пользовательских интерфейсов и определению координат элементов на изображениях.

Твоя задача: анализировать скриншоты и определять точные координаты для клика по указанному элементу.

ПРАВИЛА:
1. Внимательно изучи изображение
2. Найди указанный элемент (кнопку, поле, иконку и т.д.)
3. Определи центр этого элемента
4. Верни координаты X и Y в пикселях от левого верхнего угла
5. Укажи свою уверенность в правильности координат (high/medium/low)

ВАЖНО:
- Координата X - расстояние слева направо (0 = левый край)
- Координата Y - расстояние сверху вниз (0 = верхний край)
- Старайся попасть в центр кликабельного элемента
- Если элемент не найден или неясен - укажи low confidence

Всегда используй tool "click_coordinates" для ответа."""


def encode_image(image_path: str) -> str:
    """Кодирует изображение в base64"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def get_click_coordinates(
        image_path: str,
        instruction: str,
        api_key: str,
        image_width: int = 1920,
        image_height: int = 1080
) -> Dict:
    """
    Получает координаты клика от Claude Haiku

    Args:
        image_path: путь к изображению
        instruction: что нужно кликнуть (например, "кнопка Login")
        api_key: Anthropic API ключ
        image_width: ширина изображения в пикселях
        image_height: высота изображения в пикселях

    Returns:
        Dict с координатами и информацией о клике
    """
    client = anthropic.Anthropic(api_key=api_key)

    # Кодируем изображение
    image_data = encode_image(image_path)
    image_type = "image/png" if image_path.endswith('.png') else "image/jpeg"

    # Формируем промпт
    user_prompt = f"""На изображении найди элемент: "{instruction}"

Размер изображения: {image_width}x{image_height} пикселей

Определи точные координаты для клика по центру этого элемента и используй tool click_coordinates."""

    # Создаем запрос к API
    response = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=[CLICK_TOOL],
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": image_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": user_prompt
                    }
                ],
            }
        ],
    )

    # Обрабатываем ответ
    result = {
        "success": False,
        "x": None,
        "y": None,
        "element": None,
        "confidence": None,
        "raw_response": []
    }

    for block in response.content:
        if block.type == "text":
            result["raw_response"].append({"type": "text", "content": block.text})

        elif block.type == "tool_use" and block.name == "click_coordinates":
            result["success"] = True
            result["x"] = block.input.get("x")
            result["y"] = block.input.get("y")
            result["element"] = block.input.get("element_description")
            result["confidence"] = block.input.get("confidence")
            result["raw_response"].append({
                "type": "tool_use",
                "content": block.input
            })

    return result


def perform_click(click_data: Dict) -> None:
    """
    Выполняет клик по полученным координатам
    (здесь можно добавить реальную логику клика через pyautogui или selenium)
    """
    if not click_data["success"]:
        print("❌ Не удалось определить координаты")
        return

    x, y = click_data["x"], click_data["y"]
    element = click_data["element"]
    confidence = click_data["confidence"]

    print(f"\n✅ Координаты определены!")
    print(f"📍 Позиция: X={x}, Y={y}")
    print(f"🎯 Элемент: {element}")
    print(f"💯 Уверенность: {confidence}")

    # Пример с pyautogui (раскомментируй если нужно)
    # import pyautogui
    # pyautogui.click(x, y)

    # Пример с selenium (раскомментируй если нужно)
    # from selenium.webdriver.common.action_chains import ActionChains
    # action = ActionChains(driver)
    # action.move_by_offset(x, y).click().perform()


# Примеры использования
if __name__ == "__main__":
    API_KEY = "CHANGE_ME_ANTHROPIC_API_KEY"

    # Пример 1: Клик по кнопке
    print("=== Пример 1: Поиск кнопки ===")
    result = get_click_coordinates(
        image_path="/path/to/your/image.png",
        instruction="кликнуть по полю куда летим",
        api_key=API_KEY,
        image_width=1024,
        image_height=768
    )
    perform_click(result)

    # # Пример 2: Клик по полю ввода
    # print("\n=== Пример 2: Поиск поля ввода ===")
    # result = get_click_coordinates(
    #     image_path="form.png",
    #     instruction="поле для ввода email",
    #     api_key=API_KEY
    # )
    # perform_click(result)
    #
    # # Пример 3: Клик по иконке
    # print("\n=== Пример 3: Поиск иконки ===")
    # result = get_click_coordinates(
    #     image_path="interface.png",
    #     instruction="иконка настроек в правом верхнем углу",
    #     api_key=API_KEY
    # )
    # perform_click(result)
    #
    # # Пример 4: Получение полной информации
    # print("\n=== Пример 4: Полная информация ===")
    # result = get_click_coordinates(
    #     image_path="dashboard.png",
    #     instruction="кнопка 'Создать новый проект'",
    #     api_key=API_KEY
    # )
    # print(json.dumps(result, indent=2, ensure_ascii=False))