import asyncio
import base64
import os
from typing import List

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langfuse import get_client
from langfuse.media import LangfuseMedia
from pydantic import BaseModel, Field

from agent.schemas import ReflectionResult

from .base import BaseReflection

load_dotenv()


class ThoughtProcess(BaseModel):
    step: int
    description: str


class ClaudeReflectionResult(BaseModel):
    instruction_language: str = Field(description="Verification Instruction Language")
    thought_process: List[ThoughtProcess]
    details: str
    verification_passed: bool


class Claude35Reflection(BaseReflection):
    """Claude 3.5 Sonnet reflection model."""

    def __init__(self, inference_client=None, **kwargs):
        super().__init__(**kwargs)
        self.inference_client = inference_client
        self.langfuse = get_client()

    @classmethod
    def create_client(cls, **kwargs):
        """Create a Claude35Reflection client instance."""
        inference_client = ChatAnthropic(
            model="claude-sonnet-4-5",
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "CHANGE_ME_ANTHROPIC_API_KEY"),
            temperature=0.0,
            max_tokens=5000,
        )
        return cls(inference_client=inference_client, **kwargs)

    def encode_image(self, path_to_img: str):
        with open(path_to_img, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    async def verify_screenshot(self, image_path: str, reflection_instruction: str, retries: int = 3, logger = None,
                                **kwargs) -> ReflectionResult:
        """Verify screenshot with comprehensive Langfuse logging."""

        # Encode image
        is_base64 = kwargs.get('is_base64', False)
        if is_base64:
            encoded_image = image_path
        else:
            encoded_image = self.encode_image(image_path)

        # Create LangfuseMedia object for proper image logging
        screenshot_media = LangfuseMedia(
            content_bytes=base64.b64decode(encoded_image),
            content_type="image/jpeg",
        )

        # Define the prompt
        prompt_template = """
        You are provided with a screenshot and a verification instruction. Analyze the screenshot and perform the following steps:

        1. **Analyze the Screenshot**: Carefully examine the screenshot to identify elements relevant to the verification instruction.
        2. **Provide Detailed Explanation**: Offer a comprehensive explanation supporting your determination, referencing specific parts of the screenshot that influenced your decision.
        3. **Determine Verification Status**: Decide if the verification instruction is **True** (i.e., the condition is exactly met/passed) or **False** (i.e., the condition is not met) based on the screenshot.

        ## Note:
        - `instruction_language` is the language used in the verification instruction.
        - Answer using the same `instruction_language`as in `Verification Instruction`.

        Verification Instruction:
        {reflection_instruction}
        """.strip()

        prompt = prompt_template.replace("{reflection_instruction}", reflection_instruction)

        # Create messages for API call
        messages = [
            {"role": "user", "content": [
                {"type": "image",
                 "source": {"type": "base64", "media_type": "image/jpeg", "data": encoded_image}},
                {"type": "text", "text": prompt}
            ]}
        ]

        last_error = None

        # Start Langfuse span
        with self.langfuse.start_as_current_span(
            name="reflection_step",
            input={
                "instruction": reflection_instruction,
                "screenshot": screenshot_media,
            },
            metadata={
                "retries": retries,
                "model": "claude-sonnet-4-5",
            }
        ) as span:

            for attempt in range(retries):
                try:
                    # Update span with current attempt
                    span.update(
                        metadata={
                            "current_attempt": attempt + 1,
                            "instruction_language": reflection_instruction.split()[0] if reflection_instruction else "unknown"
                        }
                    )

                    # Request structured output from Claude using LangChain
                    model_with_parser = self.inference_client.with_structured_output(
                        ClaudeReflectionResult, include_raw=True
                    )

                    # Create manual generation span for ChatAnthropic
                    with self.langfuse.start_as_current_generation(
                        name="ChatAnthropic",
                        model="claude-sonnet-4-5",
                        input=messages,
                        model_parameters={
                            "temperature": 0.0,
                            "max_tokens": 5000,
                            "attempt": attempt + 1
                        }
                    ) as generation:
                        # Make the actual API call
                        # result_dict = model_with_parser.invoke(messages)
                        result_dict = await model_with_parser.ainvoke(messages)

                        # Extract usage information from raw response if available
                        usage_details = None
                        if isinstance(result_dict, dict) and "raw" in result_dict:
                            raw_response = result_dict["raw"]
                            if hasattr(raw_response, 'usage') and raw_response.usage:
                                usage_details = {
                                    "input_tokens": raw_response.usage.input_tokens,
                                    "output_tokens": raw_response.usage.output_tokens,
                                    "total_tokens": raw_response.usage.input_tokens + raw_response.usage.output_tokens
                                }
                            elif hasattr(raw_response, 'usage_metadata') and raw_response.usage_metadata:
                                usage_details = {
                                    "input_tokens": raw_response.usage_metadata['input_tokens'],
                                    "output_tokens": raw_response.usage_metadata['output_tokens'],
                                    "total_tokens": raw_response.usage_metadata['total_tokens']
                                }
                            else:
                                print('NO USAGE METADATA')

                        # Update generation with output and usage
                        generation.update(
                            output=result_dict.get("parsed") if isinstance(result_dict, dict) else result_dict,
                            usage_details=usage_details
                        )

                    # Extract parsed response
                    parsed_response = result_dict.get("parsed") if isinstance(result_dict, dict) else result_dict

                    # Prepare output data
                    output_data = {
                        "verification_passed": parsed_response.verification_passed if parsed_response else None,
                        "details": parsed_response.details if parsed_response else None,
                        "thought_process": [
                            {"step": tp.step, "description": tp.description}
                            for tp in (parsed_response.thought_process if parsed_response else [])
                        ],
                        "instruction_language": parsed_response.instruction_language if parsed_response else None,
                        "attempt": attempt + 1
                    }

                    # Update span with final result
                    span.update(
                        output=output_data,
                        metadata={
                            "success": True,
                            "total_attempts": attempt + 1,
                            "parsing_error": result_dict.get("parsing_error") if isinstance(result_dict, dict) else None
                        }
                    )

                    return ReflectionResult.from_claude(parsed_response)

                except Exception as e:
                    last_error = e

                    if logger:
                        logger.error(f"Error in reflection model attempt {attempt + 1}: {e}")

                    # Update span with error info
                    span.update(
                        metadata={
                            "error_attempt": attempt + 1,
                            "error_type": type(e).__name__,
                            "error_message": str(e)
                        }
                    )

                    # Check for specific error conditions
                    if 'credit balance is too low' in str(e).lower():
                        logger.error("check anthropic's balance")
                        # Don't retry for credit issues
                        break

                    continue

            # All retries failed
            span.update(
                level="ERROR",
                status_message=f"All {retries} attempts failed. Last error: {last_error}",
                metadata={
                    "success": False,
                    "total_attempts": retries,
                    "last_error_type": type(last_error).__name__ if last_error else "Unknown"
                }
            )

            raise Exception(f"Failed to call API of reflection model after {retries} attempts")

    async def verify_two_screenshots(self, before_image_path: str, after_image_path: str, reflection_instruction: str, retries: int = 3, logger = None, use_single_screenshot: bool = False, **kwargs) -> ReflectionResult:
        """Verify two screenshots (before and after) with comprehensive Langfuse logging."""

        if use_single_screenshot:
            return await self.verify_screenshot(after_image_path, reflection_instruction, retries, logger, **kwargs)

        # Encode both images
        is_base64 = kwargs.get('is_base64', False)
        if is_base64:
            encoded_before_image = before_image_path
            encoded_after_image = after_image_path
        else:
            encoded_before_image = self.encode_image(before_image_path)
            encoded_after_image = self.encode_image(after_image_path)

        # Create LangfuseMedia objects for proper image logging
        before_screenshot_media = LangfuseMedia(
            content_bytes=base64.b64decode(encoded_before_image),
            content_type="image/jpeg",
        )
        after_screenshot_media = LangfuseMedia(
            content_bytes=base64.b64decode(encoded_after_image),
            content_type="image/jpeg",
        )

        # Define the prompt for two-image comparison
        prompt_template = """
        You are provided with two screenshots (before and after) and a verification instruction. Analyze both screenshots and perform the following steps:

        1. **Analyze the Before Screenshot**: Examine the initial state shown in the first image.
        2. **Analyze the After Screenshot**: Examine the final state shown in the second image.
        3. **Compare Changes**: Identify what changes occurred between the before and after states.
        4. **Provide Detailed Explanation**: Offer a comprehensive explanation of the changes and how they relate to the verification instruction.
        5. **Determine Verification Status**: Decide if the verification instruction is **True** (i.e., the expected change occurred) or **False** (i.e., the expected change did not occur) based on comparing both screenshots.

        ## Note:
        - `instruction_language` is the language used in the verification instruction.
        - Answer using the same `instruction_language` as in `Verification Instruction`.
        - Focus on the differences between the two images and whether they match the expected outcome.

        Verification Instruction:
        {reflection_instruction}
        """.strip()

        prompt = prompt_template.replace("{reflection_instruction}", reflection_instruction)

        # Create messages for API call with both images
        messages = [
            {"role": "user", "content": [
                {"type": "text", "text": "Before screenshot:"},
                {"type": "image",
                 "source": {"type": "base64", "media_type": "image/jpeg", "data": encoded_before_image}},
                {"type": "text", "text": "After screenshot:"},
                {"type": "image",
                 "source": {"type": "base64", "media_type": "image/jpeg", "data": encoded_after_image}},
                {"type": "text", "text": prompt}
            ]}
        ]

        last_error = None

        # Start Langfuse span
        with self.langfuse.start_as_current_span(
            name="reflection_two_screenshots",
            input={
                "instruction": reflection_instruction,
                "before_screenshot": before_screenshot_media,
                "after_screenshot": after_screenshot_media,
            },
            metadata={
                "retries": retries,
                "model": "claude-sonnet-4-5",
            }
        ) as span:

            for attempt in range(retries):
                try:
                    # Update span with current attempt
                    span.update(
                        metadata={
                            "current_attempt": attempt + 1,
                            "instruction_language": reflection_instruction.split()[0] if reflection_instruction else "unknown"
                        }
                    )

                    # Request structured output from Claude using LangChain
                    model_with_parser = self.inference_client.with_structured_output(
                        ClaudeReflectionResult, include_raw=True
                    )

                    # Create manual generation span for ChatAnthropic
                    with self.langfuse.start_as_current_generation(
                        name="ChatAnthropic",
                        model="claude-sonnet-4-5",
                        input=messages,
                        model_parameters={
                            "temperature": 0.0,
                            "max_tokens": 5000,
                            "attempt": attempt + 1
                        }
                    ) as generation:
                        # Make the actual API call
                        # result_dict = model_with_parser.invoke(messages)
                        result_dict = await model_with_parser.ainvoke(messages)

                        # Extract usage information from raw response if available
                        usage_details = None
                        if isinstance(result_dict, dict) and "raw" in result_dict:
                            raw_response = result_dict["raw"]
                            if hasattr(raw_response, 'usage') and raw_response.usage:
                                usage_details = {
                                    "input_tokens": raw_response.usage.input_tokens,
                                    "output_tokens": raw_response.usage.output_tokens,
                                    "total_tokens": raw_response.usage.input_tokens + raw_response.usage.output_tokens
                                }
                            elif hasattr(raw_response, 'usage_metadata') and raw_response.usage_metadata:
                                usage_details = {
                                    "input_tokens": raw_response.usage_metadata['input_tokens'],
                                    "output_tokens": raw_response.usage_metadata['output_tokens'],
                                    "total_tokens": raw_response.usage_metadata['total_tokens']
                                }
                            else:
                                print('NO USAGE METADATA')

                        # Update generation with output and usage
                        generation.update(
                            output=result_dict.get("parsed") if isinstance(result_dict, dict) else result_dict,
                            usage_details=usage_details
                        )

                    # Extract parsed response
                    parsed_response = result_dict.get("parsed") if isinstance(result_dict, dict) else result_dict

                    # Prepare output data
                    output_data = {
                        "verification_passed": parsed_response.verification_passed if parsed_response else None,
                        "details": parsed_response.details if parsed_response else None,
                        "thought_process": [
                            {"step": tp.step, "description": tp.description}
                            for tp in (parsed_response.thought_process if parsed_response else [])
                        ],
                        "instruction_language": parsed_response.instruction_language if parsed_response else None,
                        "attempt": attempt + 1
                    }

                    # Update span with final result
                    span.update(
                        output=output_data,
                        metadata={
                            "success": True,
                            "total_attempts": attempt + 1,
                            "parsing_error": result_dict.get("parsing_error") if isinstance(result_dict, dict) else None
                        }
                    )

                    return ReflectionResult.from_claude(parsed_response)

                except Exception as e:
                    last_error = e

                    if logger:
                        logger.error(f"Error in reflection model attempt {attempt + 1}: {e}")

                    # Update span with error info
                    span.update(
                        metadata={
                            "error_attempt": attempt + 1,
                            "error_type": type(e).__name__,
                            "error_message": str(e)
                        }
                    )

                    # Check for specific error conditions
                    if 'credit balance is too low' in str(e).lower():
                        logger.error("check anthropic's balance")
                        # Don't retry for credit issues
                        break

                    continue

            # All retries failed
            span.update(
                level="ERROR",
                status_message=f"All {retries} attempts failed. Last error: {last_error}",
                metadata={
                    "success": False,
                    "total_attempts": retries,
                    "last_error_type": type(last_error).__name__ if last_error else "Unknown"
                }
            )

            raise Exception(f"Failed to call API of reflection model after {retries} attempts")
