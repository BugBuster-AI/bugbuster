import asyncio
import base64
import re
from io import BytesIO
from typing import List, Optional, Tuple

import numpy as np
from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler
from PIL import Image

from .base import BaseModel


def extract_points_tars(tars_output, image_w, image_h):
    pattern = r"\((\d+),(\d+)\)"
    matches = re.findall(pattern, tars_output)
    if len(matches) == 0:
        return np.array([0, 0], dtype=np.float32)
    point = [int(num) for num in matches[0]]
    point = np.array(point)
    point = point * np.array([image_w / 1000.0, image_h / 1000.0])
    return point


def get_centered_crop(image, x, y, size=0.5):
    width, height = image.size
    chunk_width = int(width * size)
    chunk_height = int(height * size)
    
    # Calculate the top-left corner of the chunk, centered around the point
    left = max(0, min(width - chunk_width, x - chunk_width // 2))
    top = max(0, min(height - chunk_height, y - chunk_height // 2))
    
    # Crop the image to get the chunk
    chunk = image.crop((left, top, left + chunk_width, top + chunk_height))
    
    return chunk, left, top


class TARS_v1(BaseModel):
    """Inference class for TARS v1 model."""
    
    def __init__(self, inference_ip: str):
        langfuse_handler = CallbackHandler()
        self._coordinates_client = ChatOpenAI(
            base_url=f"{inference_ip}/v1",
            model='bytedance-research/UI-TARS-7B-DPO',
            api_key="token-abc123",
            max_tokens=10,
            temperature=0.0,
            seed=0,
            # max_retries=2,
            timeout=30,
            callbacks=[langfuse_handler]
        )
        self._scroll_client = ChatOpenAI(
            base_url=f"{inference_ip}/v1",
            model='bytedance-research/UI-TARS-7B-DPO',
            api_key="token-abc123",
            max_tokens=5,
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
            model='bytedance-research/UI-TARS-7B-DPO',
            api_key="token-abc123",
            max_tokens=5,
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
        self._ocr_client = ChatOpenAI(
            base_url=f"{inference_ip}/v1",
            model='bytedance-research/UI-TARS-7B-DPO',
            api_key="token-abc123",
            max_tokens=40,
            temperature=0.0,
            seed=0,
            # max_retries=2,
            timeout=30,
            callbacks=[langfuse_handler],
        )
        self._coordinates_prompt = r"""<|im_start|>system
            You are a helpful assistant.<|im_end|>
            <|im_start|>user
            You are a GUI agent. You are given an element description and a screenshot. You need to return click coordinates of the element. 

            ## Output Format
            ```\n(x, y)```

            ## User Instruction
            """
        self._scroll_prompt = "Is there a {} in the image? Respond with score from 0 to 100 which describes your confidence that the element which exactly matches the description is present on the image. Look for exact text match. Your response should be a single number between 0 and 100."
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
        no_negative: bool = False
    ) -> Tuple[int, int]:
        """Get coordinates for an element in an image using a two-step process."""
        image = Image.open(image_path)
        prompt = self._coordinates_prompt + task

        # First step - get rough coordinates
        output = await self._send_request(self._coordinates_client, image, prompt)
        x1, y1 = extract_points_tars(output, image.size[0], image.size[1])

        # Second step - get precise coordinates from cropped image
        crop, left, top = get_centered_crop(image, x1, y1)
        output = await self._send_request(self._coordinates_client, crop, prompt)

        x2, y2 = extract_points_tars(output, crop.size[0], crop.size[1])
        if not (x2 == 0 and y2 == 0):
            x2 += left
            y2 += top
            x, y = round(x2), round(y2)
        else:
            x, y = x1, y1

        return x, y
    
    async def get_scroll_scores(
        self,
        image_path: str,
        element_description: str,
        crop_len: int = 900,
        crops: Optional[List[str]] = None
    ) -> List[int]:
        """Detect elements in a scrollable area."""
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