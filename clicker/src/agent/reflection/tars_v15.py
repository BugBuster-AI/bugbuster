import base64

from langchain_openai import ChatOpenAI
from langfuse import get_client
from langfuse.langchain import CallbackHandler
from pydantic import BaseModel, Field

from agent.schemas import ReflectionResult

from .base import BaseReflection


class TarsV15ReflectionResult(BaseModel):
    instruction_language: str = Field(description="Verification Instruction Language")
    chain_of_thoughts: str = Field(description="Concise Thoughts")
    details: str
    verification_passed: bool


class TarsV15Reflection(BaseReflection):
    """TARS v15 reflection model."""
    
    def __init__(self, inference_client=None, **kwargs):
        super().__init__(**kwargs)
        self.inference_client = inference_client
        self.langfuse = get_client()
    
    @classmethod
    def create_client(cls, inference_ip: str, **kwargs):
        """Create a TarsV15Reflection client instance with ChatOpenAI client."""
        langfuse_handler = CallbackHandler()
        inference_client = ChatOpenAI(
            base_url=f"{inference_ip}/v1",
            model='screenmate-v2',
            api_key="token-abc123",
            max_tokens=1000,
            temperature=0.1,
            seed=0,
            callbacks=[langfuse_handler]
        )
        return cls(inference_client=inference_client, **kwargs)
    
    def encode_image(self, path_to_img: str):
        with open(path_to_img, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    async def verify_screenshot(self, image_path: str, reflection_instruction: str, retries: int = 1, logger = None, **kwargs) -> ReflectionResult:

        is_base64 = kwargs.get('is_base64', False)
        if is_base64:
            encoded_string = image_path
        else:
            encoded_string = self.encode_image(image_path)

        prompt = f"""
        You are provided with a screenshot and a verification instruction. Analyze the screenshot and perform the following steps:
        
        1. **Analyze the Screenshot**: Carefully examine the screenshot to identify elements relevant to the verification instruction. 
        2. **Provide Detailed Explanation**: Offer a comprehensive explanation supporting your determination, referencing specific parts of the screenshot that influenced your decision.
        3. **Determine Verification Status**: Decide if the verification instruction is **True** (i.e., the condition is exactly met/passed) or **False** (i.e., the condition is not met) based on the screenshot.

        ## Note:
        - Answer using the same `instruction_language`as in `Verification Instruction` in `chain_of_thoughts` part.
        
        Verification Instruction:
        {reflection_instruction}
        """.strip()
        prompt = prompt.replace("{reflection_instruction}", reflection_instruction)

        with self.langfuse.start_as_current_span(
            name="reflection_step",
            input={
                "instruction": reflection_instruction,
            },
            metadata={
                "retries": retries,
                "model": "tars-v15",
            }
        ) as span:
            for attempt in range(retries):
                try:
                    span.update(metadata={"current_attempt": attempt + 1})
                    messages = [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_string}"}},
                            ],
                        },
                    ]
                    model_with_parser = self.inference_client.with_structured_output(TarsV15ReflectionResult)
                    # response = model_with_parser.invoke(messages)
                    response = await model_with_parser.ainvoke(messages)

                    return ReflectionResult.from_tars_v15(response)
                except Exception as e:
                    if logger:
                        logger.error(f"Error in reflection model: {e}")
                    continue
        raise Exception("Failed to call API of reflection model")

    async def verify_two_screenshots(self, before_image_path: str, after_image_path: str, reflection_instruction: str, retries: int = 1, logger = None, use_single_screenshot: bool = False, **kwargs) -> ReflectionResult:
        """Enhanced two-screenshot verification with fallback to single screenshot."""

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

            prompt = f"""
            You are provided with two screenshots (before and after) and a verification instruction. Analyze both screenshots and perform the following steps:

            1. **Analyze the Before Screenshot**: Examine the initial state shown in the first image.
            2. **Analyze the After Screenshot**: Examine the final state shown in the second image.
            3. **Compare Changes**: Identify what changes occurred between the before and after states.
            4. **Provide Detailed Explanation**: Offer a comprehensive explanation of the changes and how they relate to the verification instruction.
            5. **Determine Verification Status**: Decide if the verification instruction is **True** (i.e., the expected change occurred) or **False** (i.e., the expected change did not occur) based on comparing both screenshots.

            ## Note:
            - Answer using the same `instruction_language` as in `Verification Instruction` in `chain_of_thoughts` part.
            - Focus on the differences between the two images and whether they match the expected outcome.

            Verification Instruction:
            {reflection_instruction}
            """.strip()
            prompt = prompt.replace("{reflection_instruction}", reflection_instruction)

            with self.langfuse.start_as_current_span(
                name="reflection_two_screenshots",
                input={
                    "instruction": reflection_instruction,
                },
                metadata={
                    "retries": retries,
                    "model": "tars-v15",
                }
            ) as span:
                for attempt in range(retries):
                    try:
                        span.update(metadata={"current_attempt": attempt + 1})
                        messages = [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": "Before screenshot:"},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_before_string}"}},
                                    {"type": "text", "text": "After screenshot:"},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_after_string}"}},
                                    {"type": "text", "text": prompt},
                                ],
                            },
                        ]
                        model_with_parser = self.inference_client.with_structured_output(TarsV15ReflectionResult)
                        # response = model_with_parser.invoke(messages)
                        response = await model_with_parser.ainvoke(messages)

                        return ReflectionResult.from_tars_v15(response)
                    except Exception as e:
                        if logger:
                            logger.error(f"Error in two-screenshot reflection model: {e}")
                        continue
                raise Exception("Failed to call API of two-screenshot reflection model")
        except Exception as e:
            if logger:
                logger.warning(f"Two-screenshot verification failed, falling back to single screenshot: {e}")
            return await self.verify_screenshot(after_image_path, reflection_instruction, retries, logger, **kwargs)