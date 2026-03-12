import asyncio
import base64

from langchain_openai import ChatOpenAI
from langfuse import get_client
from langfuse.langchain import CallbackHandler
from langfuse.media import LangfuseMedia
from pydantic import BaseModel, Field

from agent.schemas import ReflectionResult
from core.config import INFERENCE_API_KEY, INFERENCE_MODEL_NAME, OPENROUTER_PROVIDER_EXTRA_BODY

from .base import BaseReflection

MAX_RETRIES = 3
RETRY_DELAY = 10


class Qwen3VLReflectionResult(BaseModel):
    instruction_language: str = Field(description="Verification Instruction Language")
    thought_process: str = Field(description="Concise Thoughts")
    details: str
    verification_passed: bool


class Qwen3VLReflection(BaseReflection):
    """Qwen3-VL reflection model."""

    def __init__(self, inference_client=None, **kwargs):
        super().__init__(**kwargs)
        self.inference_client = inference_client
        self.langfuse = get_client()

    @classmethod
    def create_client(cls, inference_ip: str, **kwargs):
        """Create a Qwen3VLReflection client instance with ChatOpenAI client."""
        langfuse_handler = CallbackHandler()
        base_url = inference_ip.rstrip("/")
        if not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"
        client_kwargs = {}
        if "openrouter.ai" in base_url and OPENROUTER_PROVIDER_EXTRA_BODY:
            client_kwargs["extra_body"] = OPENROUTER_PROVIDER_EXTRA_BODY
        inference_client = ChatOpenAI(
            base_url=base_url,
            model=INFERENCE_MODEL_NAME,
            api_key=INFERENCE_API_KEY,
            max_tokens=1000,
            temperature=0.1,
            seed=0,
            callbacks=[langfuse_handler],
            **client_kwargs
        )
        return cls(inference_client=inference_client, **kwargs)

    def encode_image(self, path_to_img: str):
        with open(path_to_img, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    async def verify_screenshot(self, image_path: str, reflection_instruction: str, retries: int = 1, logger=None,
                                **kwargs) -> ReflectionResult:

        is_base64 = kwargs.get('is_base64', False)
        if is_base64:
            encoded_string = image_path
        else:
            encoded_string = self.encode_image(image_path)

        system_prompt = """
            You are a GUI analysis agent, and you are currently working with **Web Browser** platform. You will be provided with the following resources:
            1.  The first image is final state.

            Analyze the provided screenshot and perform the following: examine the screenshot to identify elements relevant to the verification instruction; provide a comprehensive explanation supporting your determination, referencing specific parts of the screenshot that influenced your decision; and decide whether the verification instruction is True (condition exactly met/passed) or False (condition not met) based on the screenshot.

            Your response should be formatted as follows:
            {
            "instruction_language": "...",
            "thought_process": "...",
            "details": "...",
            "verification_passed": bool,
            }

            ## Important Notes:
            - The `instruction_language` field should identify the language of the instruction (e.g., "Russian", "English", "Spanish").
            - CRITICAL: Field `details` must be completed in the LANGUAGE specified in the field instruction_language.

            RETURN THE DICTIONARY IN STRICT JSON FORMAT:
        """.strip()

        prompt = f"""
        Verification Instruction:
        {reflection_instruction}
        """
        prompt = prompt.replace("{reflection_instruction}", reflection_instruction)

        screenshot_media = LangfuseMedia(
            content_bytes=base64.b64decode(encoded_string),
            content_type="image/jpeg",
        )

        with self.langfuse.start_as_current_span(
                name="reflection_step",
                input={
                    "instruction": reflection_instruction,
                    "screenshot": screenshot_media,
                },
                metadata={
                    "retries": retries,
                    "model": "qwen3-vl",
                }
        ) as span:
            for attempt in range(retries):
                try:
                    span.update(metadata={"current_attempt": attempt + 1})
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
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_string}"}},
                                {"type": "text", "text": prompt},
                            ],
                        },
                    ]
                    model_with_parser = self.inference_client.with_structured_output(Qwen3VLReflectionResult)
                    # response = model_with_parser.invoke(messages)
                    response = await model_with_parser.ainvoke(messages)

                    return ReflectionResult.from_qwen3_vl(response)
                except Exception as e:
                    if logger:
                        logger.error(f"Error in reflection model (attempt {attempt + 1}/{retries}): {e}")
                    if attempt < retries - 1:
                        if logger:
                            logger.info(f"Waiting {RETRY_DELAY}s before retry...")
                        await asyncio.sleep(RETRY_DELAY)
                    continue
        raise Exception("Failed to call API of reflection model")

    async def verify_two_screenshots(self, before_image_path: str, after_image_path: str, reflection_instruction: str,
                                     retries: int = 1, logger=None, use_single_screenshot: bool = False, **kwargs) -> ReflectionResult:
        """Enhanced two-screenshot verification with fallback to single screenshot."""
        if logger:
            logger.info(f"use_single_screenshot = {use_single_screenshot}")
        if use_single_screenshot:
            return await self.verify_screenshot(after_image_path, reflection_instruction, retries, logger, **kwargs)

        try:

            is_base64 = kwargs.get('is_base64', False)
            if is_base64:
                encoded_before_string = before_image_path
                encoded_after_string = after_image_path
            else:
                encoded_before_string = self.encode_image(before_image_path)
                encoded_after_string = self.encode_image(after_image_path)

            system_prompt = """
            You are a GUI analysis agent, and you are currently working with a **Web Browser** platform. You will be provided with the following resources:
            1.  The first image is initial state.
            2.  The second image is final state.

            Analyze the differences between two consecutive GUI screenshots, identify what changes occurred between the before and after states, provide a comprehensive explanation of the changes and how they relate to the verification instruction, and decide if the verification instruction is True (the expected change occurred) or False (the expected change did not occur) based on comparing both screenshots;

            Your response should be formatted as follows:
            {
            "instruction_language": "...",
            "thought_process": "...",
            "details": "...",
            "verification_passed": bool,
            }

            ## Important Notes:
            - The `instruction_language` field should identify the language of the instruction (e.g., "Russian", "English", "Spanish").
            - CRITICAL: Field `details` must be completed in the LANGUAGE specified in the field instruction_language.
            - Focus on the differences between the two images and whether they match the expected outcome.

            RETURN THE DICTIONARY IN STRICT JSON FORMAT:
            """.strip()

            prompt = f"""
            Verification Instruction:
            {reflection_instruction}
            """
            prompt = prompt.replace("{reflection_instruction}", reflection_instruction)

            before_screenshot_media = LangfuseMedia(
                content_bytes=base64.b64decode(encoded_before_string),
                content_type="image/jpeg",
            )
            after_screenshot_media = LangfuseMedia(
                content_bytes=base64.b64decode(encoded_after_string),
                content_type="image/jpeg",
            )

            with self.langfuse.start_as_current_span(
                    name="reflection_two_screenshots",
                    input={
                        "instruction": reflection_instruction,
                        "before_screenshot": before_screenshot_media,
                        "after_screenshot": after_screenshot_media,
                    },
                    metadata={
                        "retries": retries,
                        "model": "qwen3-vl",
                    }
            ) as span:
                for attempt in range(retries):
                    try:
                        span.update(metadata={"current_attempt": attempt + 1})
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
                                    {"type": "image_url",
                                     "image_url": {"url": f"data:image/jpeg;base64,{encoded_before_string}",
                                                   "detail": "auto"}},
                                    {"type": "image_url",
                                     "image_url": {"url": f"data:image/jpeg;base64,{encoded_after_string}",
                                                   "detail": "auto"}},
                                    {"type": "text", "text": prompt},
                                ],
                            },
                        ]
                        model_with_parser = self.inference_client.with_structured_output(Qwen3VLReflectionResult)
                        # response = model_with_parser.invoke(messages)
                        response = await model_with_parser.ainvoke(messages)

                        return ReflectionResult.from_qwen3_vl(response)
                    except Exception as e:
                        if logger:
                            logger.error(f"Error in two-screenshot reflection model (attempt {attempt + 1}/{retries}): {e}")
                        if _is_retryable_http_error(e) and attempt < retries - 1:
                            if logger:
                                logger.info(f"Retryable HTTP error, waiting {HTTP_RETRY_DELAY}s before retry...")
                            await asyncio.sleep(HTTP_RETRY_DELAY)
                        continue
                raise Exception("Failed to call API of two-screenshot reflection model")
        except Exception as e:
            if logger:
                logger.warning(f"Two-screenshot verification failed, falling back to single screenshot: {e}")
            return await self.verify_screenshot(after_image_path, reflection_instruction, retries, logger, **kwargs)
