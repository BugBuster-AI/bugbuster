import asyncio
import base64
import math
import re
from io import BytesIO
from typing import List, Optional, Tuple

from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler
from PIL import Image

from .base import BaseModel

IMAGE_FACTOR = 28
MIN_PIXELS = 100 * 28 * 28
# MAX_PIXELS = 16384 * 28 * 28
MAX_PIXELS = 3688000 #(2560x1440 roughly) bigger pictures would require too much memory
MAX_RATIO = 200

# Common resolutions with diverse aspect ratios
COMMON_RESOLUTIONS = [
    # Horizontal (Landscape)
    (1932, 1092),  # 16:9 - 1080p would be resized to this by smart_resize
    (2560, 1440),  # 16:9 - common high-res
    (3440, 1440),  # 21:9 - ultrawide
    (2560, 1080),  # 21:9 - ultrawide 1080p
    (1680, 1050),  # 16:10 - classic widescreen
    (1440, 900),   # 16:10 - smaller 16:10
    (1366, 768),   # 16:9-ish - common laptop
    
    # Vertical (Portrait)
    (1080, 1920),  # 9:16 - mobile portrait
    (1440, 2560),  # 9:16 - high-res mobile
    (1080, 2560),  # 9:21 - ultrawide portrait
    (1050, 1680),  # 10:16 - tablet portrait
    
    # Square-ish
    (1200, 1200),  # 1:1 - square
]

def find_best_resolution(width: int, height: int) -> Tuple[int, int]:
    """Find the best common resolution that can contain the input dimensions."""
    input_ratio = width / height
    
    # Filter resolutions that can contain the input image
    candidates = [(w, h) for w, h in COMMON_RESOLUTIONS if w >= width and h >= height]
    
    if not candidates:
        # If no common resolution fits, return the largest one
        return max(COMMON_RESOLUTIONS, key=lambda x: x[0] * x[1])
    
    # Score candidates by aspect ratio similarity and size efficiency
    def score_resolution(w, h):
        ratio = w / h
        ratio_diff = abs(ratio - input_ratio)
        size_efficiency = (width * height) / (w * h)  # Higher is better
        return size_efficiency - ratio_diff * 0.5  # Weight ratio similarity
    
    return max(candidates, key=lambda res: score_resolution(res[0], res[1]))

def pad_to_resolution(image: Image.Image, target_width: int, target_height: int) -> Tuple[Image.Image, int, int]:
    """Pad image to target resolution, centering the original image."""
    original_width, original_height = image.size
    
    # Calculate padding
    pad_left = (target_width - original_width) // 2
    pad_top = (target_height - original_height) // 2
    
    # Create new image with target resolution
    padded_image = Image.new('RGB', (target_width, target_height), color=(0, 0, 0))
    
    # Paste original image in the center
    padded_image.paste(image, (pad_left, pad_top))
    
    return padded_image, pad_left, pad_top

def round_by_factor(number: int, factor: int) -> int:
    """Returns the closest integer to 'number' that is divisible by 'factor'."""
    return round(number / factor) * factor

def ceil_by_factor(number: int, factor: int) -> int:
    """Returns the smallest integer greater than or equal to 'number' that is divisible by 'factor'."""
    return math.ceil(number / factor) * factor

def floor_by_factor(number: int, factor: int) -> int:
    """Returns the largest integer less than or equal to 'number' that is divisible by 'factor'."""
    return math.floor(number / factor) * factor

def smart_resize(
    height: int, width: int, factor: int = IMAGE_FACTOR, min_pixels: int = MIN_PIXELS, max_pixels: int = MAX_PIXELS
) -> tuple[int, int]:
    """
    Rescales the image so that the following conditions are met:

    1. Both dimensions (height and width) are divisible by 'factor'.

    2. The total number of pixels is within the range ['min_pixels', 'max_pixels'].

    3. The aspect ratio of the image is maintained as closely as possible.
    """
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

def extract_points_tars_v15(tars_output, original_w, original_h, padded_w, padded_h, pad_left, pad_top, smart_resize_w, smart_resize_h):
    pattern = r"\((\d+),(\d+)\)"
    matches = re.findall(pattern, tars_output)
    if len(matches) == 0:
        return 0, 0
    
    # Get coordinates from model output (in smart_resize space)
    model_x, model_y = int(matches[0][0]), int(matches[0][1])
    
    # Transform from smart_resize space to padded space
    scale_x = padded_w / smart_resize_w
    scale_y = padded_h / smart_resize_h
    padded_x = model_x * scale_x
    padded_y = model_y * scale_y
    
    # Transform from padded space to original space
    original_x = padded_x - pad_left
    original_y = padded_y - pad_top
    
    # Clamp to original image bounds
    original_x = max(0, min(original_w, original_x))
    original_y = max(0, min(original_h, original_y))
    
    return round(original_x), round(original_y)


class TARS_v15(BaseModel):
    def __init__(self, inference_ip: str):
        langfuse_handler = CallbackHandler()
        self._coordinates_client = ChatOpenAI(
            base_url=f"{inference_ip}/v1",
            model='screenmate-v2',
            api_key="token-abc123",
            max_tokens=15,
            temperature=0.0,
            seed=0,
            # max_retries=2,
            timeout=30,
            callbacks=[langfuse_handler]
        )
        self._scroll_client = ChatOpenAI(
            base_url=f"{inference_ip}/v1",
            model='screenmate-v2',
            api_key="token-abc123",
            max_tokens=10,
            temperature=0.0,
            seed=0,
            # max_retries=2,
            timeout=30,
            callbacks=[langfuse_handler],
            extra_body={
                "guided_regex": r"^([0-9]|[1-9][0-9]|100)$",
                "stop": ["\n"]
            },
        )
        self._detection_client = ChatOpenAI(
            base_url=f"{inference_ip}/v1",
            model='screenmate-v2',
            api_key="token-abc123",
            max_tokens=10,
            temperature=0.0,
            seed=0,
            # max_retries=2,
            timeout=30,
            callbacks=[langfuse_handler],
        )
        self._ocr_client = ChatOpenAI(
            base_url=f"{inference_ip}/v1",
            model='screenmate-v2',
            api_key="token-abc123",
            max_tokens=50,
            temperature=0.0,
            seed=0,
            # max_retries=2,
            timeout=30,
            callbacks=[langfuse_handler],
        )
        self._coordinates_prompt = r"""<|im_start|>system
            You are a helpful assistant.<|im_end|>
            <|im_start|>user
            You are a GUI agent. You are given a task description and a screenshot. You need to return coordinates of the element that matches the task. If there is no element that matches the task, reply with 'NO' instead of coordinates.  

            ## User Instruction
            """
        self._coordinates_prompt_noneg = r"""<|im_start|>system
            You are a helpful assistant.<|im_end|>
            <|im_start|>user
            You are a GUI agent. You are given a task description and a screenshot. You need to return coordinates of the element that matches the task.

            ## User Instruction
            """
        self._scroll_prompt = "Is there a {} on the image? Respond with score from 0 to 100 which describes your confidence that the element which exactly matches the description is present on the image. Look for exact text match.\nYour response should be a single number between 0 and 100."
        self._detection_prompt = "Is there an element described as: {} in the image? Respond with score from 0 to 100 where 100 means that the element is definitely present in the image, reduce the score if you think that the page or the element have not been fully loaded yet. Your response should be a single number between 0 and 100."
        self._ocr_prompt = r"""<|im_start|>system
            You are a helpful assistant.<|im_end|>
            <|im_start|>user
            You are a GUI agent. You are given a task description and a screenshot. You need to parse the text corresponding to the task from the image. Your response should only contain the text corresponding to the task and nothing else.  

            ## User Instruction
            """

    async def _send_request(
        self,
        client: ChatOpenAI,
        image: Image.Image,
        prompt: str,
    ) -> str:
        """Send a request with an image to the model."""
        buffered = BytesIO()
        image.save(buffered, format="jpeg")
        encoded_string = base64.b64encode(buffered.getvalue()).decode('utf-8')

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_string}"}},
                ],
            },
        ]

        # response = client.invoke(messages)
        response = await client.ainvoke(messages)
        return response.content
    
    async def get_coordinates(
        self,
        image_path: str,
        task: str,
        no_negative: bool = False,
        is_base64: bool = False,
        context_screenshot_image_path: str = None,
        context_screenshot_is_base64: bool = False,

    ) -> Tuple[int, int]:
        """Get coordinates for an element in an image using a two-step process."""
        # Load original image
        if is_base64:
            image_data = base64.b64decode(image_path)
            original_image = Image.open(BytesIO(image_data))
        else:
            original_image = Image.open(image_path)

        # контекстная картинка (опциональная: с ручки приходит в base_64, в ране с диска)
        if context_screenshot_image_path:
            if context_screenshot_is_base64:
                with Image.open(BytesIO(base64.b64decode(context_screenshot_image_path))):
                    pass
            else:
                with Image.open(context_screenshot_image_path):
                    pass

        original_w, original_h = original_image.size
        
        # Step 1: Pad to common resolution
        target_w, target_h = find_best_resolution(original_w, original_h)
        padded_image, pad_left, pad_top = pad_to_resolution(original_image, target_w, target_h)
        
        # Step 2: Apply smart resize
        smart_resize_h, smart_resize_w = smart_resize(padded_image.size[1], padded_image.size[0])
        final_image = padded_image.resize((smart_resize_w, smart_resize_h))
        
        print(f"Original: {original_w}x{original_h} → Padded: {target_w}x{target_h} → Final: {smart_resize_w}x{smart_resize_h}")
        
        prompt = (self._coordinates_prompt_noneg if no_negative else self._coordinates_prompt) + task
        
        output = await self._send_request(self._coordinates_client, final_image, prompt)
        print(output)
        
        # Transform coordinates back to original image space
        x, y = extract_points_tars_v15(
            output, 
            original_w, original_h,
            target_w, target_h, 
            pad_left, pad_top,
            smart_resize_w, smart_resize_h
        )

        return x, y
    
    async def get_scroll_scores(
        self,
        image_path: str,
        element_description: str,
        crop_len: int = 900,
        crops: Optional[List[str]] = None
    ) -> Tuple[int, int]:
        """Get coordinates for an element in an image using a two-step process."""
        if crops is None:
            crops = []
        if crops == [] and isinstance(crops, list):
            image = Image.open(image_path)
            for i in range(image.size[1] // crop_len):
                crops.append(image.crop((0, i * crop_len, image.size[0], (i + 1) * crop_len)))
            if image.size[1] % crop_len > 0:
                crops.append(image.crop((0, image.size[1] - crop_len, image.size[0], image.size[1])))
        else:
            crops = [Image.open(image_path) for image_path in crops]
        
        prompt = self._scroll_prompt.format(element_description)
        tasks = [self._send_request(self._scroll_client, crop, prompt) for crop in crops]
        results = await asyncio.gather(*tasks)
        return [int(float(result)) for result in results]
    
    async def get_detection_confidence(
        self,
        image_path: str,
        element_description: str,
    ) -> int:
        image = Image.open(image_path)
        prompt = self._detection_prompt.format(element_description)
        output = await self._send_request(self._detection_client, image, prompt)
        return int(output)
    
    async def ocr(
        self,
        image_path: str,
        instruction: str,
    ) -> str:
        image = Image.open(image_path)
        prompt = self._ocr_prompt + instruction
        output = await self._send_request(self._ocr_client, image, prompt)
        return output
