import asyncio
from typing import Any, Dict, List

from pydantic import ValidationError

from agent.rewriter.pydantic_schemas import (
    MultiActionSteps,
    RewriterActionPlan,
)
from core.config import (
    OPENROUTER_PROVIDER_EXTRA_BODY,
    SOP_REWRITER_API_KEY,
    SOP_REWRITER_BASE_URL,
    SOP_REWRITER_MODEL_NAME,
    SOP_REWRITER_PROVIDER,
    logger,
)
from core.model_resolver import resolve_model_url
from llm_controller import LLMProvider, create_llm_service

MAX_RETRIES = 3
RETRY_DELAY = 10

response_schema = {
  "type": "object",
  "properties": {
    "actions": {
      "type": "array",
      "description": "List of actions.",
      "items": {
        "anyOf": [
          {
            "title": "Click Action",
            "type": "object",
            "properties": {
              "action_type": { "type": "string", "enum": ["CLICK"] },
              "element_description": { "type": "string", "description": "Comprehensive description of the element including name, type, position, and other distinguishing attributes like color or size. Example: \"Login button at the top right corner\", \"Red delete icon next to the user name\"." }
            },
            "required": ["action_type", "element_description"]
          },
          {
            "title": "Type Action",
            "type": "object",
            "properties": {
              "action_type": { "type": "string", "enum": ["TYPE"] },
              "text_to_type": { "type": "string", "description": "Text to type. Should be kept exactly as is." },
              "element_description": { "type": "string", "description": "Comprehensive description of the input element including name, type, position, and other distinguishing attributes like size. Example: \"Email address input field\", \"Search box at the top of the page\"." }
            },
            "required": ["action_type", "text_to_type", "element_description"]
          },
          {
            "title": "Hover Action",
            "type": "object",
            "properties": {
                "action_type": { "type": "string", "enum": ["HOVER"] },
                "element_description": { "type": "string", "description": "Comprehensive description of the element including name, type, position, and other distinguishing attributes like color or size. Example: \"Settings dropdown menu\", \"User avatar in the top bar\"." }
            },
            "required": ["action_type", "element_description"]
          },
          {
              "title": "Clear Action",
              "type": "object",
              "properties": {
                  "action_type": { "type": "string", "enum": ["CLEAR"] },
                  "element_description": { "type": "string", "description": "Comprehensive description of the input element including name, type, position, and other distinguishing attributes like size. Example: \"Password field\", \"Search input in the navigation bar\"." }
              },
              "required": ["action_type", "element_description"]
          },
          {
            "title": "Press Action",
            "type": "object",
            "properties": {
              "action_type": { "type": "string", "enum": ["PRESS"], "description": "Action used to press a keyboard key or combination of keys." },
              "key_to_press": { "type": "string", "description": "Key or combination of keys to press. Example: 'Enter', 'Ctrl+KeyA', 'Shift+Tab'." }
            },
            "required": ["action_type", "key_to_press"]
          },
          {
              "title": "Scroll Action",
              "type": "object",
              "properties": {
                  "action_type": { "type": "string", "enum": ["SCROLL"], "description": "Action used to scroll the page to the target element." },
                  "scroll_target": { "type": "string", "description": "Comprehensive description of the scroll target element including name, type, position, and other distinguishing attributes like color or size. Example: \"Table at the bottom of the page\", \"Comments section\"." }
              },
              "required": ["action_type", "scroll_target"]
          },
          {
              "title": "Inner Scroll Action",
              "type": "object",
              "properties": {
                  "action_type": { "type": "string", "enum": ["INNER_SCROLL"], "description": "Action used to scroll scrollable container to the target element." },
                  "container_description": { "type": "string", "description": "Comprehensive description of the scrollable container including name, type, position, and other distinguishing attributes. Example: \"Language selection dropdown\", \"Left sidebar with user list\"." },
                  "scroll_target": { "type": "string", "description": "Name/text of the target element to scroll into view. Example: \"Русский\", \"Today's meeting\", \"'Telegramm' icon\"." }
              },
              "required": ["action_type", "container_description", "scroll_target"]
          },
          {
              "title": "Wait Action",
              "type": "object",
              "properties": {
                  "action_type": { "type": "string", "enum": ["WAIT"], "description": "Action used to wait for a specific element to appear or just wait for a certain time period." },
                  "wait_time": { "type": "number", "format": "float", "description": "Time to wait in SECONDS, if not specified, use default value of 30 seconds." },
                  "element_description": { "type": "string", "description": "Optional: Comprehensive description of the element to wait for. Only include if user asked to wait for specific element. Example: \"Loading spinner\", \"Confirmation dialog\"." }
              },
              "required": ["action_type", "wait_time"]
          },
          {
            "title": "New Tab Action",
            "type": "object",
            "properties": {
              "action_type": { "type": "string", "enum": ["NEW_TAB"] },
              "tab_name": { "type": "string", "description": "URL for new tab." }
            },
            "required": ["action_type", "tab_name"]
          },
          {
            "title": "Switch Tab Action",
            "type": "object",
            "properties": {
              "action_type": { "type": "string", "enum": ["SWITCH_TAB"] },
              "tab_name": { "type": "string", "description": "URL or title of tab to switch to." }
            },
            "required": ["action_type", "tab_name"]
          },
          {
            "title": "Read Action",
            "type": "object",
            "properties": {
              "action_type": { "type": "string", "enum": ["READ"] },
              "instruction": { "type": "string", "description": "What text to read/extract from the screen. Keep exactly as provided by user." },
              "storage_key": { "type": "string", "description": "Variable name to store the read text under, without curly braces. Example: for {{verification_code}} use \"verification_code\"." }
            },
            "required": ["action_type", "instruction", "storage_key"]
          },
          {
            "title": "Select Action",
            "type": "object",
            "properties": {
              "action_type": { "type": "string", "enum": ["SELECT"], "description": "Action used to select an option from a dropdown or select element." },
              "element_description": { "type": "string", "description": "Comprehensive description of the select/dropdown element including name, type, position, and other distinguishing attributes. Example: \"Sort by dropdown\", \"Language selection menu\"." },
              "option_value": { "type": "string", "description": "Value or visible text of the option to select from the dropdown. Keep exactly as provided by user. Example: \"date\", \"Ипотека для IT\"." }
            },
            "required": ["action_type", "element_description", "option_value"]
          },
          {
            "title": "Unsupported Action",
            "type": "object",
            "properties": {
              "action_type": { "type": "string", "enum": ["UNSUPPORTED"], "description": "Action used to indicate that the step is not a valid action." },
              "reason": { "type": "string", "description": "Explanation of why this action is unsupported. For example, if the step is not a valid action for inputs like 'Swipe image to the right' return explanation of why it's not a valid action." }
            },
            "required": ["action_type", "reason"]
          }
        ]
      }
    }
  },
  "required": [ "actions" ]
}

def _get_sop_request_args(provider: LLMProvider, timeout: float = 30.0) -> Dict[str, Any]:
    args: Dict[str, Any] = {"timeout": timeout}
    if provider == LLMProvider.VLLM:
        args["extra_body"] = {"chat_template_kwargs": {"enable_thinking": False}}
    elif (
        provider == LLMProvider.OPENAI
        and SOP_REWRITER_BASE_URL
        and "openrouter.ai" in SOP_REWRITER_BASE_URL
        and OPENROUTER_PROVIDER_EXTRA_BODY
    ):
        args["extra_body"] = OPENROUTER_PROVIDER_EXTRA_BODY
    return args



system_instruction = """
**Task:**  
You will be given an action plan in natural language from a manual QA engineer. The plan is a list of steps to test the website, steps are separated only by a new line symbol. Your task is to convert it into a structured JSON object that adheres strictly to the provided `response_schema`.
Each individual action should be represented as an `Action` object within the `actions` array. Ensure that all necessary fields are accurately extracted and formatted as valid JSON.
Each Action object together with a screenshot of the website will be used as an input for a VLM (Vision Language Model), which will try to perform the action using the screenshot.

For each step you must first determine the type of action to perform from the following list:
- CLICK
- TYPE
- HOVER
- SCROLL
- CLEAR
- PRESS
- INNER_SCROLL
- WAIT
- NEW_TAB
- SWITCH_TAB
- READ
- SELECT
- UNSUPPORTED

If you cannot convert the step into a valid action, return an UNSUPPORTED action with the reason.

Given action plan can have variables "{{variable_name}}". You should keep variables as is in the output generated schema. Variables should be properly located in the schema.


GUIDELINES:

**General guidelines:**
- After choosing the action type, you must fill the fields of the action object with the appropriate values. Do not add any information which in not present in the original step.
- IF information for required field is missing, fill it with placeholder [MISSING]. Only use placeholder for the fields that are required, for optional fields just skip them.
- If a single step contains multiple actions, you should return UNSUPPORTED action with the reason.

**Cross-Step References:**
When steps reference previous actions, include full context in each step since the VLM processes each action independently.
- Input: ["Scroll down to the yellow shirt", "Click add to cart button below it"]  
- Output: Second action should reference "add to cart button below the yellow shirt"

**WAIT actions:**
- If the instruction specifies how long to wait (e.g., “3 секунды”, “5 seconds”), return that value as wait_time in seconds and element_description must always be null.
- Do NOT extract only the text in quotes - include the full context and qualifying phrases

**Guideline for inputs in other languages:**
- Keep all visible UI text exactly as it appears (button labels, menu items, etc.)
- Translate only the descriptive parts to English
- Example: For a instruction in russian "нажать на кнопку 'Пополнить баланс'" you should return "click on 'Пополнить баланс' button".

**Important rules for READ actions and variables:**
- READ action is used to extract and store information from the page (OCR).
- If an instruction contains read/copy keywords and contains a variable in the format `{{var_name}}`, generate READ action.
- For that READ action, set `storage_key` to the variable name without curly braces.

**READ Example:**
Input:
Считай название раздела с коллекцией для йоги в переменную {{yoga_section}}
Correct Output:
```json
[
  {
    "action_type": "READ",
    "instruction": "Считай название раздела с коллекцией для йоги в переменную {{yoga_section}}",
    "storage_key": "yoga_section"
  }
]
```

**Important rules for PRESS actions:**
- PRESS action is used for keyboard key presses
- When you see key combinations with modifiers (shift+enter, ctrl+c, cmd+v, alt+tab, etc.), this should be represented as a SINGLE PRESS action
- Examples:
  - "нажать Enter" → {"action_type": "PRESS", "key_to_press": "Enter"}
  - "нажать shift+enter" → {"action_type": "PRESS", "key_to_press": "Shift+Enter"}
- **CRITICAL: Never split key combinations into separate PRESS actions. "Shift+Enter" is ONE action, not two.**


**Important note for SCROLL and INNER_SCROLL actions:**
- Use SCROLL when scrolling the entire page to bring an element into view
- Use INNER_SCROLL when scrolling within a specific container (dropdown, sidebar, modal)
- Examples:
  - "Scroll down to the footer" → SCROLL action
  - "Scroll through the dropdown to find 'Advanced Settings'" → INNER_SCROLL action
- Important exception: if instruction clearly states to use inner scroll, you must use INNER_SCROLL action, even if element is a 'page'.

**Note for UNSUPPORTED actions:**
- Return UNSUPPORTED if you cannot convert the step into a valid action.
- If user want check or validate something return UNSUPPORTED and at the reason return "use reflection step" on query language

**Example:**
input:
кликнуть
response:
0: {
    action_type: "CLICK"
    element_description: "[MISSING]"
}
input:
кликнуть на кнопку входа
response:
0: {
    action_type: "CLICK"
    element_description: "кнопка входа"
}
"""

prompt = """
{sop}
"""

multi_action_system_instruction = """
You are an analyzer that detects which original instruction steps were expanded into multiple actions.

You will receive:
1. Original instructions (numbered list from user)
2. Rewritten action plan (list of actions produced by the system)

Your task is to compare them and identify which ORIGINAL step numbers resulted in MORE THAN ONE action in the rewritten plan.

For example:
- If original step 3 "Click login and enter password" became 2 actions (CLICK + TYPE), return 3
- If original step 5 "Clear field, type text, press Enter" became 3 actions, return 5

Return ONLY the original step numbers (as integers, 1-based) that contain multiple actions. If all original steps map to exactly one action each, return an empty list.
"""

multi_action_prompt = """
Compare the original instructions with the rewritten action plan and return the original step numbers that resulted in multiple actions.

ORIGINAL INSTRUCTIONS:
{numbered_steps}

REWRITTEN ACTION PLAN:
{action_plan_formatted}
"""


async def detect_multi_action_steps(sop: str, action_plan: List[Dict[str, Any]], ip_retries: int = 3) -> List[int]:
    lines = [line.strip() for line in sop.strip().split('\n') if line.strip()]
    numbered_steps = "\n".join([f"{i + 1}. {line}" for i, line in enumerate(lines)])

    action_plan_formatted = "\n".join([
        f"{i + 1}. {action.get('action_type', 'UNKNOWN')}: {action}"
        for i, action in enumerate(action_plan)
    ])

    provider = LLMProvider(SOP_REWRITER_PROVIDER.lower())

    url_or_id = SOP_REWRITER_BASE_URL
    try:
        base_url = await resolve_model_url(url_or_id)
    except ValueError as e:
        logger.error(f"Failed to resolve SOP rewriter URL: {e}")
        return []

    client = create_llm_service(
        provider=provider,
        api_key=SOP_REWRITER_API_KEY,
        base_url=base_url
    )

    messages = [
        {"role": "system", "content": multi_action_system_instruction},
        {"role": "user", "content": multi_action_prompt.format(
            numbered_steps=numbered_steps,
            action_plan_formatted=action_plan_formatted
        )},
    ]

    for attempt in range(MAX_RETRIES):
        try:
            response = await client.fetch_completion(
                model=SOP_REWRITER_MODEL_NAME,
                messages=messages,
                response_clazz=MultiActionSteps,
                args=_get_sop_request_args(provider=provider),
            )

            if isinstance(response, str):
                result = MultiActionSteps.model_validate_json(response)
            else:
                result = MultiActionSteps.model_validate(response)

            return result.step_numbers

        except Exception as e:
            logger.warning(
                f"Error in detect_multi_action_steps (attempt {attempt + 1}/{MAX_RETRIES}): {e}"
            )
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY)
                continue
            return []

    return []


async def rewrite_sop(sop: str, retries=1, ip_retries=3) -> List[Dict[str, Any]]:
    provider = LLMProvider(SOP_REWRITER_PROVIDER.lower())

    url_or_id = SOP_REWRITER_BASE_URL
    base_url = await resolve_model_url(url_or_id)

    client = create_llm_service(
        provider=provider,
        api_key=SOP_REWRITER_API_KEY,
        base_url=base_url
    )

    contents = prompt.replace("{sop}", sop)
    model_name = SOP_REWRITER_MODEL_NAME
    messages = None

    for attempt in range(retries):
        current_contents = contents

        if not messages:
            messages = [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": current_contents},
            ]

        for http_attempt in range(MAX_RETRIES):
            try:
                response = await client.fetch_completion(
                    model=model_name,
                    messages=messages,  # type: ignore
                    response_clazz=RewriterActionPlan,
                    args=_get_sop_request_args(provider=provider),
                )

                try:
                    if isinstance(response, str):
                        action_plan = RewriterActionPlan.model_validate_json(response)
                    else:
                        action_plan = RewriterActionPlan.model_validate(response)

                    return [action.dict() for action in action_plan.actions]

                except ValidationError:
                    if attempt == retries - 1:
                        raise Exception(
                            f"Validation failed after {retries}"
                        )
                    break

            except Exception as e:
                logger.error(
                    f"Error rewriting SOP (attempt {http_attempt + 1}/{MAX_RETRIES}): {e}",
                    exc_info=True,
                )
                if http_attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                break

    raise Exception(
        f"Failed to rewrite SOP after {retries} retries: 'The system is temporarily unavailable. Please try again later.'"
    )


async def main(instruction: str):
    result = await rewrite_sop(instruction)
    logger.info(result)


if __name__ == "__main__":
    # print(RewriterActionPlan.model_json_schema())
    asyncio.run(
        main("""Добавить текущую страницу в закладки.
Навести курсор на элемент "Загрузить файлы".
Прочитать текст с экрана о доступных тарифах и функциях Dropbox.
Ожидать загрузки страницы после перехода на сайт Dropbox.
Добавить страницу в закладки.
Прокрутить список файлов до элемента с названием "Документы".
Уменьшить масштаб страницы для лучшего просмотра содержимого.
Считать текст с экрана для последующего использования.
переключиться на вкладку с документами
Ожидать загрузки страницы Dropbox.
Прокрутить страницу вниз до раздела с последними загруженными файлами.
Навести курсор на элемент "Загрузить файлы".
Навести курсор на элемент "Загрузить файлы".
переключиться на другую вкладку
Считать текст с экрана для дальнейшего использования.
"Температура должна быть целочисленным значением"
"проверь, что на странице более 2 карточек товара с носками"
"Проверить что во всех карточках цена в \"$\""
"Проверить что во всех карточках валюта в USD"
"Проверить что во всех карточках цена в USD"
"Проверить что во всех карточках валюта в \"$\""
"Проверить что во всех карточках валюта \"$\""
"проверь что корзина пустая"
"проверь что корзина пустая"
"на странице поиска нет результатов"
"откроется другая страница с результатами поиска"
"Проверь что все цифровые значения имеют нулевые параметры"
"Проверь, что сообщение появилось в чате"
"Проверь, что сообщение появилось в чате"
"Проверить, что сообщение появилось в чате"
"Проверь, что сообщение отправилось"
"Проверить, что сообщение отправилось"
"Проверить, что сообщение появилось в чате"
""")
    )
