import asyncio
import base64
import json
import math
import re
from enum import Enum
from io import BytesIO
from typing import List, Optional, Tuple

from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler
from PIL import Image
from pydantic import BaseModel, Field

from core.config import INFERENCE_API_KEY, INFERENCE_MODEL_NAME, OPENROUTER_PROVIDER_EXTRA_BODY, logger

from .base import BaseModel as AgentBaseModel

IMAGE_FACTOR = 28
MIN_PIXELS = 100 * 28 * 28
MAX_PIXELS = 3688000
MAX_RATIO = 200

COMMON_RESOLUTIONS = [
    (1932, 1092),
    (2560, 1440),
    (3440, 1440),
    (2560, 1080),
    (1680, 1050),
    (1440, 900),
    (1366, 768),
    (1080, 1920),
    (1440, 2560),
    (1080, 2560),
    (1050, 1680),
    (1200, 1200),
]


class YesNoAnswer(str, Enum):
    YES = "YES"
    NO = "NO"


def extract_coordinates_from_json(output: str, image_w: int, image_h: int) -> Tuple[int, int]:
    try:
        data = json.loads(output)
        if "coordinates" in data:
            x, y = data["coordinates"][0], data["coordinates"][1]
            x = max(0, min(image_w, int(x)))
            y = max(0, min(image_h, int(y)))
            return x, y
        return 0, 0
    except (json.JSONDecodeError, ValueError, KeyError, IndexError):
        return 0, 0


def find_best_resolution(width: int, height: int) -> Tuple[int, int]:
    input_ratio = width / height
    candidates = [(w, h) for w, h in COMMON_RESOLUTIONS if w >= width and h >= height]

    if not candidates:
        return max(COMMON_RESOLUTIONS, key=lambda x: x[0] * x[1])

    def score_resolution(w, h):
        ratio = w / h
        ratio_diff = abs(ratio - input_ratio)
        size_efficiency = (width * height) / (w * h)
        return size_efficiency - ratio_diff * 0.5

    return max(candidates, key=lambda res: score_resolution(res[0], res[1]))


def pad_to_resolution(image: Image.Image, target_width: int, target_height: int) -> Tuple[Image.Image, int, int]:
    original_width, original_height = image.size
    pad_left = (target_width - original_width) // 2
    pad_top = (target_height - original_height) // 2
    padded_image = Image.new('RGB', (target_width, target_height), color=(0, 0, 0))
    padded_image.paste(image, (pad_left, pad_top))
    return padded_image, pad_left, pad_top


def round_by_factor(number: int, factor: int) -> int:
    return round(number / factor) * factor


def ceil_by_factor(number: int, factor: int) -> int:
    return math.ceil(number / factor) * factor


def floor_by_factor(number: int, factor: int) -> int:
    return math.floor(number / factor) * factor


def smart_resize(
        height: int, width: int, factor: int = IMAGE_FACTOR, min_pixels: int = MIN_PIXELS, max_pixels: int = MAX_PIXELS
) -> tuple[int, int]:
    if max(height, width) / min(height, width) > MAX_RATIO:
        raise ValueError(
            f"absolute aspect ratio must be smaller than {MAX_RATIO}, got {max(height, width) / min(height, width)}"
        )
    h_bar = max(factor, round_by_factor(height, factor))
    w_bar = max(factor, round_by_factor(width, factor))
    if h_bar * w_bar > max_pixels:
        beta = math.sqrt((height * width) / max_pixels)
        h_bar = floor_by_factor(height / beta, factor)
        w_bar = floor_by_factor(width / beta, factor)
    elif h_bar * w_bar < min_pixels:
        beta = math.sqrt(min_pixels / (height * width))
        h_bar = ceil_by_factor(height * beta, factor)
        w_bar = ceil_by_factor(width * beta, factor)
    return h_bar, w_bar


def transform_coordinates_back(
        model_x: int, model_y: int,
        original_w: int, original_h: int,
        padded_w: int, padded_h: int,
        pad_left: int, pad_top: int,
        smart_resize_w: int, smart_resize_h: int
) -> Tuple[int, int]:
    scale_x = padded_w / smart_resize_w
    scale_y = padded_h / smart_resize_h
    padded_x = model_x * scale_x
    padded_y = model_y * scale_y

    original_x = padded_x - pad_left
    original_y = padded_y - pad_top

    original_x = max(0, min(original_w, original_x))
    original_y = max(0, min(original_h, original_y))

    return round(original_x), round(original_y)


def extract_yes_no_from_json(output: str) -> int:
    try:
        data = json.loads(output)
        if "answer" in data:
            if data["answer"].upper() == "YES":
                return 90
            elif data["answer"].upper() == "NO":
                return 10
        return 50
    except (json.JSONDecodeError, KeyError):
        return 50


def extract_yes_no_from_text(output: str) -> int:
    if not output:
        return 50
    upper_output = output.upper()
    if "YES" in upper_output:
        return 90
    if "NO" in upper_output:
        return 10
    return 50


def extract_yes_no_token(output: str) -> Optional[bool]:
    if not output:
        return None

    normalized = output.strip().lower()
    if normalized in {"yes", "true"}:
        return True
    if normalized in {"no", "false"}:
        return False

    if "yes" in normalized or "true" in normalized:
        return True
    if "no" in normalized or "false" in normalized:
        return False

    return None


def parse_tool_call_from_string(response_text: str) -> Optional[dict]:
    """
    Парсит tool_call из строки формата:
    '<tool_call>
    {"name": "click", "arguments": {"coordinate": [185, 756]}}
    </tool_call>'

    Возвращает словарь с 'name' и 'arguments' или None если не удалось распарсить.
    """
    try:
        # Ищем содержимое между тегами <tool_call> и </tool_call>
        match = re.search(r'<tool_call>\s*(.*?)\s*</tool_call>', response_text, re.DOTALL)
        if not match:
            return None

        json_str = match.group(1).strip()
        data = json.loads(json_str)

        return data
    except (json.JSONDecodeError, AttributeError, KeyError):
        return None



class CoordinatesResult(BaseModel):
    coordinates: List[int] = Field(description="X and Y coordinates as [x, y]")


class YesNoResult(BaseModel):
    answer: bool = Field(description="Whether the element is present on the screen")


class OCRResult(BaseModel):
    extracted_text: str = Field(description="The extracted text from the image")


class Qwen3VL(AgentBaseModel):
    def __init__(self, inference_ip: str):
        self.inference_ip = inference_ip
        base_url = inference_ip.rstrip("/")
        if not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"
        self._base_url = base_url

        langfuse_handler = CallbackHandler()
        client_kwargs = {}
        if "openrouter.ai" in base_url and OPENROUTER_PROVIDER_EXTRA_BODY:
            client_kwargs["extra_body"] = OPENROUTER_PROVIDER_EXTRA_BODY

        self._coordinates_client = ChatOpenAI(
            base_url=base_url,
            model=INFERENCE_MODEL_NAME,
            api_key=INFERENCE_API_KEY,
            max_tokens=30,
            temperature=0.0,
            seed=0,
            timeout=30,
            callbacks=[langfuse_handler],
            **client_kwargs
        )

        self._scroll_client = ChatOpenAI(
            base_url=base_url,
            model=INFERENCE_MODEL_NAME,
            api_key=INFERENCE_API_KEY,
            max_tokens=100,
            temperature=0.0,
            seed=0,
            timeout=30,
            callbacks=[langfuse_handler],
            **client_kwargs
        )

        self._detection_client = ChatOpenAI(
            base_url=base_url,
            model=INFERENCE_MODEL_NAME,
            api_key=INFERENCE_API_KEY,
            max_tokens=100,
            temperature=0.0,
            seed=0,
            timeout=30,
            callbacks=[langfuse_handler],
            **client_kwargs
        )

        self._ocr_client = ChatOpenAI(
            base_url=base_url,
            model=INFERENCE_MODEL_NAME,
            api_key=INFERENCE_API_KEY,
            max_tokens=80,
            temperature=0.0,
            seed=0,
            timeout=30,
            callbacks=[langfuse_handler],
            **client_kwargs
        )

        self._reasoning_client = ChatOpenAI(
            base_url=base_url,
            model=INFERENCE_MODEL_NAME,
            api_key=INFERENCE_API_KEY,
            max_tokens=100,
            temperature=0.3,
            seed=0,
            timeout=30,
            callbacks=[langfuse_handler],
            **client_kwargs
        )

    def _create_coordinates_prompt(self, display_width_px: int, display_height_px: int, has_context_image: bool = False) -> str:
        base_prompt =  f"""
You are a helpful assistant.

* The screen's resolution is {display_width_px}x{display_height_px}.
* If an element is not found on the screen, return the text "not found".
* Always identify exactly where to click. If the instruction refers to a specific UI element (e.g., search bar, button, icon), ensure you select and interact with that precise element.
* If the instruction mentions a property such as color, shape, or text, confirm that the selected element visually and contextually matches those properties before interacting.
* If text is written inside quotation marks ("example"), check that the element's text fully and exactly matches the quoted string before selecting or interacting.
* if user instruction is not click, you must click on the element which is described in instruction
"""

        if has_context_image:
            context_instructions = """
        IMAGE ANALYSIS INSTRUCTIONS:

        You are provided with two images in the following order:
        1. First image (Context Screenshot): Shows the target element highlighted with a red box. This image helps you understand what element you need to find.
        2. Second image (Main Screenshot): Shows the full screen where you need to locate and click the element.

        HOW TO USE THE IMAGES:
        - Use the context image to understand which element you are looking for (the element inside the red highlighted box).
        - Use the main image to find where that same element is located and click on it.
        - The context image provides visual reference; the main image is where you perform the click action.
        - Look for the same visual characteristics (color, text, shape, icon) in both images to identify the element in the main screenshot.
        - Provide coordinates based on the main image (the second image).
        """
            return base_prompt + context_instructions

        return base_prompt

    def _create_yes_no_prompt(self) -> str:
        return """
You are a helpful assistant.

* Your task is to find an element on the screen and answer either True or False based on whether the element is present on the screen.

Your response should be formatted as follows:
{
"answer": bool,
}

RETURN THE DICTIONARY IN STRICT JSON FORMAT:
"""

    def _create_ocr_prompt(self) -> str:
        return """
Your task is to extract text from the provided image according to the user’s specific instructions.
Carefully analyze the image. Follow the user’s instruction exactly to determine which text should be extracted. Perform all reasoning internally.

*Rules*
Extract only the text that is both:
explicitly visible in the image, and
explicitly requested by the user’s instruction.
Do not infer, complete, translate, summarize, or paraphrase any text.
Do not include any text that is not visible in the image.
Do not repeat or reference the user’s instruction unless that exact text appears in the image.
If the text requested by the user is not visible in the image, return an empty string.

Your output MUST be a valid JSON object that strictly matches the following schema:

{
  "extracted_text": "string"
}

Return only the JSON object.
No explanations, no markdown, no additional text.
"""

    def _create_reasoning_prompt(self) -> str:
        return """
You are a helpful assistant analyzing a screen to understand where to click.

Analyze the image and the task carefully. Think step by step about:
1. What elements are visible on the screen
2. Which element matches the task description
3. Where exactly that element is located
4. Why this is the correct element to click

Provide your reasoning in 2-3 sentences.
"""

    async def _send_request_structured(
            self,
            client: ChatOpenAI,
            image: Image.Image,
            system_prompt: str,
            prompt: str,
            response_model
    ):

        buffered = BytesIO()
        image.save(buffered, format="jpeg")
        encoded_string = base64.b64encode(buffered.getvalue()).decode('utf-8')

        messages = [
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": system_prompt}
                ]
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_string}"}},
                ],
            },
        ]

        model_with_parser = client.with_structured_output(response_model)
        # response = model_with_parser.invoke(messages)
        response = await model_with_parser.ainvoke(messages)
        return response

    def smart_resize(
            height: int, width: int, factor: int = 28, min_pixels: int = 56 * 56, max_pixels: int = 14 * 14 * 4 * 1280
    ):
        """Rescales the image so that the following conditions are met:

        1. Both dimensions (height and width) are divisible by 'factor'.

        2. The total number of pixels is within the range ['min_pixels', 'max_pixels'].

        3. The aspect ratio of the image is maintained as closely as possible.

        """
        if max(height, width) / min(height, width) > 200:
            raise ValueError(
                f"absolute aspect ratio must be smaller than 200, got {max(height, width) / min(height, width)}"
            )
        h_bar = round(height / factor) * factor
        w_bar = round(width / factor) * factor
        if h_bar * w_bar > max_pixels:
            beta = math.sqrt((height * width) / max_pixels)
            h_bar = max(factor, math.floor(height / beta / factor) * factor)
            w_bar = max(factor, math.floor(width / beta / factor) * factor)
        elif h_bar * w_bar < min_pixels:
            beta = math.sqrt(min_pixels / (height * width))
            h_bar = math.ceil(height * beta / factor) * factor
            w_bar = math.ceil(width * beta / factor) * factor
        return h_bar, w_bar

    async def get_coordinates(
            self,
            image_path: str,
            task: str,
            no_negative: bool = False,
            is_base64: bool = False,
            context_screenshot_image_path: str = None,
            context_screenshot_is_base64: bool = False,
    ) -> Tuple[int, int]:
        logger.info(f"{self.inference_ip}")
        logger.info("get_coordinates request: prompt")
        if is_base64:
            logger.info("base64")
            image_data = base64.b64decode(image_path)
            original_image = Image.open(BytesIO(image_data))
        else:
            original_image = Image.open(image_path)

        # контекстная картинка (опциональная: с ручки приходит в base_64, в ране с диска)
        context_image = None
        if context_screenshot_image_path:
            if context_screenshot_is_base64:
                context_image = Image.open(BytesIO(base64.b64decode(context_screenshot_image_path)))
            else:
                context_image = Image.open(context_screenshot_image_path)
        logger.info(f"context_image: {type(context_image)} path={context_screenshot_image_path}")

        original_w, original_h = original_image.size

        resized_height, resized_width = smart_resize(
            original_image.height,
            original_image.width,
            factor=32,
            min_pixels=3136,
            max_pixels=12845056,
        )

        print(
            f"Original: {original_w}x{original_h} → Final: {resized_width}x{resized_height}")

        # Define click tool
        click_tool = {
            "type": "function",
            "function": {
                "name": "click",
                "description": "Click on an element at the specified coordinates",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "coordinate": {
                            "description": "(x, y): The x (pixels from the left edge) and y (pixels from the top edge) coordinates to move the mouse to.",
                            "type": "array",
                            "items": {"type": "integer"},
                            "minItems": 2,
                            "maxItems": 2
                        }
                    },
                    "required": ["coordinate"]
                }
            }
        }
        has_context_image = context_image is not None
        system_prompt = self._create_coordinates_prompt(1000, 1000, has_context_image)
        prompt = task

        image_to_encode = original_image
        if image_to_encode.mode == 'RGBA':
            rgb_image = Image.new('RGB', image_to_encode.size, (255, 255, 255))
            rgb_image.paste(image_to_encode, mask=image_to_encode.split()[3])
            image_to_encode = rgb_image
        elif image_to_encode.mode != 'RGB':
            image_to_encode = image_to_encode.convert('RGB')

        buffered = BytesIO()
        image_to_encode.save(buffered, format="jpeg")
        encoded_string = base64.b64encode(buffered.getvalue()).decode('utf-8')

        user_content = [
            {"type": "text", "text": prompt},
        ]

        if context_image:
            context_image_to_encode = context_image
            if context_image_to_encode.mode == 'RGBA':
                rgb_context = Image.new('RGB', context_image_to_encode.size, (255, 255, 255))
                rgb_context.paste(context_image_to_encode, mask=context_image_to_encode.split()[3])
                context_image_to_encode = rgb_context
            elif context_image_to_encode.mode != 'RGB':
                context_image_to_encode = context_image_to_encode.convert('RGB')

            buffered_context = BytesIO()
            context_image_to_encode.save(buffered_context, format="jpeg")
            encoded_context_string = base64.b64encode(buffered_context.getvalue()).decode('utf-8')

            user_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_context_string}"}})

        user_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_string}"}})

        messages = [
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": system_prompt}
                ]
            },
            {
                "role": "user",
                "content": user_content,
            },
        ]

        model_with_tools = self._coordinates_client.bind_tools([click_tool])
        response = None
        try:
            response = await model_with_tools.ainvoke(messages)
        except Exception as e:
            # vLLM may return tool_calls.args as a list [x, y] instead of dict {"coordinate": [x, y]}
            # which causes langchain pydantic validation to fail.
            # Fall through to raw API call.
            logger.warning(f"bind_tools ainvoke failed, trying raw API call: {e}")

        # Проверяем, есть ли tool_calls в response объекте
        if response is not None and hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                if tool_call['name'] == 'click':
                    args = tool_call['args']
                    coordinates = args if isinstance(args, list) else args.get('coordinate', [])
                    if len(coordinates) >= 2:
                        model_x, model_y = coordinates[0], coordinates[1]
                        return int(model_x / 1000 * resized_width), int(model_y / 1000 * resized_height)

        # Fallback: raw API call without bind_tools to handle malformed tool_calls
        if response is None:
            try:
                from openai import AsyncOpenAI
                raw_client = AsyncOpenAI(
                    base_url=self._base_url,
                    api_key=INFERENCE_API_KEY,
                )
                raw_response = await raw_client.chat.completions.create(
                    model=self._coordinates_client.model_name,
                    messages=messages,
                    tools=[click_tool],
                    max_tokens=30,
                    temperature=0.0,
                    seed=0,
                )
                choice = raw_response.choices[0]
                if choice.message.tool_calls:
                    for tc in choice.message.tool_calls:
                        if tc.function.name == 'click':
                            args = json.loads(tc.function.arguments)
                            if isinstance(args, list) and len(args) >= 2:
                                model_x, model_y = args[0], args[1]
                                return int(model_x / 1000 * resized_width), int(model_y / 1000 * resized_height)
                            elif isinstance(args, dict):
                                coordinates = args.get('coordinate', [])
                                if len(coordinates) >= 2:
                                    model_x, model_y = coordinates[0], coordinates[1]
                                    return int(model_x / 1000 * resized_width), int(model_y / 1000 * resized_height)
                # Also try parsing content as text
                if choice.message.content:
                    response_text = choice.message.content
                    logger.info(f"Raw API response text: {response_text}")
                    tool_call_data = parse_tool_call_from_string(response_text)
                    if tool_call_data and tool_call_data.get('name') == 'click':
                        arguments = tool_call_data.get('arguments', {})
                        if isinstance(arguments, list):
                            coordinates = arguments
                        else:
                            coordinates = arguments.get('coordinate', [])
                        if len(coordinates) >= 2:
                            model_x, model_y = coordinates[0], coordinates[1]
                            return int(model_x / 1000 * resized_width), int(model_y / 1000 * resized_height)
                logger.info("Raw API call: element not found")
                return 0, 0
            except Exception as raw_e:
                logger.error(f"Raw API call also failed: {raw_e}")
                return 0, 0

        # Если не нашли tool_calls, пробуем парсить как строку с XML тегами
        response_text = None
        if hasattr(response, 'content'):
            response_text = response.content
        elif isinstance(response, str):
            response_text = response

        if response_text:
            logger.info(f"Response text: {response_text}")
            tool_call_data = parse_tool_call_from_string(response_text)
            if tool_call_data and tool_call_data.get('name') == 'click':
                arguments = tool_call_data.get('arguments', {})
                if isinstance(arguments, list):
                    coordinates = arguments
                else:
                    coordinates = arguments.get('coordinate', [])
                if len(coordinates) >= 2:
                    model_x, model_y = coordinates[0], coordinates[1]
                    logger.info(f"Parsed coordinates from string: x={model_x}, y={model_y}")
                    return int(model_x / 1000 * resized_width), int(model_y / 1000 * resized_height)

        # If no tool call was made, element not found
        logger.info("Element not found - no click tool call")
        return 0, 0

    async def get_scroll_scores(
            self,
            image_path: str,
            element_description: str,
            crop_len: int = 900,
            crops: Optional[List[str]] = None,
            is_base64: bool = False
    ) -> List[int]:
        if crops is None:
            crops = []

        crop_paths = []
        if not crops:
            image = Image.open(image_path)
            temp_crops = []
            for i in range(image.size[1] // crop_len):
                crop = image.crop((0, i * crop_len, image.size[0], (i + 1) * crop_len))
                temp_crops.append(crop)
            if image.size[1] % crop_len > 0:
                crop = image.crop((0, image.size[1] - crop_len, image.size[0], image.size[1]))
                temp_crops.append(crop)

            for crop in temp_crops:
                buffered = BytesIO()
                crop.save(buffered, format="jpeg")
                crop_paths.append(buffered.getvalue())
        else:
            crop_paths = crops

        tasks = [
            self._get_scroll_crop_confidence(crop_data, element_description)
            for crop_data in crop_paths
        ]
        scores = await asyncio.gather(*tasks)

        return scores

    async def _get_scroll_crop_confidence(
            self,
            crop_data,
            element_description: str,
    ) -> int:
        if isinstance(crop_data, bytes):
            encoded_string = base64.b64encode(crop_data).decode('utf-8')
        else:
            image = Image.open(crop_data)
            buffered = BytesIO()
            image.save(buffered, format="jpeg")
            encoded_string = base64.b64encode(buffered.getvalue()).decode('utf-8')

        system_prompt = self._create_yes_no_prompt()
        prompt = f"Element description: {element_description}"

        messages = [
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": system_prompt}
                ]
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_string}"}},
                ],
            },
        ]

        response = await self._scroll_client.ainvoke(messages,
                                                     logprobs=True,
                                                     top_logprobs=5)

        tt = self.get_target_token_probability(response, 4, ' true', ' false')
        if tt is None:
            response_text = getattr(response, "content", "") or ""
            if not isinstance(response_text, str):
                response_text = str(response_text)
            yes_no_token = extract_yes_no_token(response_text)
            if yes_no_token is True:
                return 100
            if yes_no_token is False:
                return 0
            return 0

        return int(tt * 100) if tt else 0

    def get_target_token_probability(self, response, step_index, target_token, f_target_token):
        # Попытка получить структуру логпробов
        meta = getattr(response, "response_metadata", None)
        if not meta or "logprobs" not in meta:
            return None  # нет логпробов в ответе

        logprobs_meta = meta.get("logprobs")
        if not isinstance(logprobs_meta, dict):
            return None

        logprobs_content = logprobs_meta.get("content")
        if not logprobs_content or len(logprobs_content) <= step_index:
            return None

        top = logprobs_content[step_index].get("top_logprobs")
        if top is None:
            return None

        # Приводим top_logprobs к виду {token: logprob}
        if isinstance(top, dict):
            token_to_logprob = top
        else:
            # Возможна форма: список словарей/объектов
            token_to_logprob = {}
            for entry in top:
                if isinstance(entry, dict) and "token" in entry and "logprob" in entry:
                    token_to_logprob[entry["token"]] = entry["logprob"]
                elif isinstance(entry, dict):
                    # может быть словарь {token: logprob} внутри списка
                    for k, v in entry.items():
                        token_to_logprob[k] = v
                else:
                    # неизвестный формат — пропускаем
                    continue

        if not token_to_logprob:
            return None

        # Найдём логпроб целевого токена (если есть)
        if target_token not in token_to_logprob:
            # токен не в top-k -> невозможно корректно восстановить его вероятность из этих данных
            return None

        target_lp = math.exp(token_to_logprob.get(target_token, float('-inf')))
        f_target_lp = math.exp(token_to_logprob.get(f_target_token, float('-inf')))
        # стабильный log-sum-exp
        prob = target_lp / (target_lp + f_target_lp)

        logger.info(f"prob: {prob}, token: {logprobs_content[step_index]['token']}")
        # if logprobs_content[step_index]['token'] == ' true':
        #     return 0.99
        return prob  # число в [0,1]

    async def get_detection_confidence(
            self,
            image_path: str,
            element_description: str,
    ) -> int:
        image = Image.open(image_path)

        if image.mode == 'RGBA':
            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
            rgb_image.paste(image, mask=image.split()[3])
            image = rgb_image
        elif image.mode != 'RGB':
            image = image.convert('RGB')

        buffered = BytesIO()
        image.save(buffered, format="jpeg")
        encoded_string = base64.b64encode(buffered.getvalue()).decode('utf-8')

        system_prompt = self._create_yes_no_prompt()
        prompt = f"Element description: {element_description}"

        messages = [
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": system_prompt}
                ]
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_string}"}},
                ],
            },
        ]

        response = await self._detection_client.ainvoke(messages,
                                                        logprobs=True,
                                                        top_logprobs=5)

        tt = self.get_target_token_probability(response, 4, ' true', ' false')
        if tt is None:
            response_text = getattr(response, "content", "") or ""
            if not isinstance(response_text, str):
                response_text = str(response_text)
            yes_no_token = extract_yes_no_token(response_text)
            if yes_no_token is True:
                return 100
            if yes_no_token is False:
                return 0
            return 0

        return int(tt * 100) if tt else 0

    async def ocr(
            self,
            image_path: str,
            instruction: str,
    ) -> str:
        image = Image.open(image_path)
        width, height = image.size

        system_prompt = self._create_ocr_prompt()
        prompt = f"User instruction: {instruction}"

        result = await self._send_request_structured(
            self._ocr_client, image, system_prompt, prompt, OCRResult
        )

        return result.extracted_text

    def _create_element_description_prompt(self, more_info) -> str:
        if not more_info:
            return """
You are an assistant that analyzes UI elements on screenshots.

The target element is inside a highlighted area.  
You must NOT describe, mention, reference, or interpret the highlight box in any way.  
Ignore its color, shape, size, borders, and position entirely.

Describe ONLY the UI element located inside the highlight, as if you intend to click it.

The description must follow this strict sequence of attributes:

1. Element color  
2. Shape and visual features (rounded corners, borders, shadows)  
3. Element type (button, input field, icon, toggle, etc.)  
4. Exact visible text, if any  
5. Unique identifier (icon, symbol, image, position, etc.)  
6. Screen position (e.g., top left, bottom right, centered)  
7. Interface context if clearly readable (e.g., “inside the search bar”, “in the navigation panel”)

Output format: a single linear description that combines all attributes into one concise phrase.  
Example structure: “yellow rectangular button with rounded corners ‘Catalog’ with a hamburger-menu icon, located at the top left inside the main navigation bar.”
"""
        return """
        You are an assistant that analyzes UI elements on screenshots.

        The target element is inside a highlighted area.  
        You must NOT describe, mention, reference, or interpret the highlight box in any way.  
        Ignore its color, shape, size, borders, and position entirely.

        Describe ONLY the UI element located inside the highlight, as if you intend to click it.

        The description must follow this strict sequence of attributes:

        1. Element color  
        2. Shape and visual features (rounded corners, borders, shadows)  
        3. Element type (button, input field, icon, toggle, etc.)  
        4. Exact visible text, if any  
        5. Unique identifier (icon, symbol, image, position, etc.)  
        6. Screen position (e.g., top left, bottom right, centered)  
        7. Interface context if clearly readable (e.g., “inside the search bar”, “in the navigation panel”)
        8. Elements located nearby and the relative position of the target element compared to them (e.g., “to the right of the search field”, “above the settings icon”)
 
        
        Output format: a single linear description that combines all attributes into one concise phrase.  
        Example structure: “yellow rectangular button with rounded corners ‘Catalog’ with a hamburger-menu icon, located at the top left inside the main navigation bar.”
        """

    async def describe_element(
            self,
            image_path: str,
            x1: int,
            y1: int,
            x2: int,
            y2: int,
            color,
            is_base64: bool = False,
            thinking_mode: bool = True,
            previous_description: Optional[str] = None
    ) -> str:
        color_value = color.value if hasattr(color, 'value') else str(color)

        color_map = {
            'red': (255, 0, 0),
            'blue': (0, 0, 255),
            'green': (0, 255, 0)
        }
        rgb_color = color_map.get(color_value.lower(), (255, 0, 0))

        if is_base64:
            image_data = base64.b64decode(image_path)
            image = Image.open(BytesIO(image_data))
        else:
            image = Image.open(image_path)

        if image.mode == 'RGBA':
            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
            rgb_image.paste(image, mask=image.split()[3])
            image = rgb_image
        elif image.mode != 'RGB':
            image = image.convert('RGB')

        from PIL import ImageDraw
        image_with_box = image.copy()
        draw = ImageDraw.Draw(image_with_box)
        draw.rectangle([x1, y1, x2, y2], outline=rgb_color, width=3)

        buffered = BytesIO()
        image_with_box.save(buffered, format="jpeg")
        encoded_string = base64.b64encode(buffered.getvalue()).decode('utf-8')

        system_prompt = self._create_element_description_prompt(bool(previous_description))

        prompt = f"Отвечай на русском. Я выделил элемент {color_value} прямоугольником. НЕ ПИШИ ПРО {color_value.upper()} КВАДРАТ"

        if previous_description:
            prompt += f"\n\nPrevious description that didn't work: \"{previous_description}\"\nPlease provide a different and more accurate description."

        messages = [
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": system_prompt}
                ]
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_string}"}},
                ],
            },
        ]

        response = await self._reasoning_client.ainvoke(messages)

        if hasattr(response, 'content'):
            return response.content
        elif isinstance(response, str):
            return response

        return str(response)
