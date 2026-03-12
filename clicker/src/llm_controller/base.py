import inspect
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Type

from langfuse import get_client, observe
from openai import AsyncOpenAI
from pydantic import BaseModel


class LLMProvider(str, Enum):
    OPENAI = "openai"
    VLLM = "vllm"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"


def _get_caller_info() -> Dict[str, str]:
    frame = inspect.currentframe()
    try:
        caller_frame = frame.f_back.f_back.f_back
        if caller_frame:
            filename = caller_frame.f_code.co_filename.split('/')[-1]
            function_name = caller_frame.f_code.co_name
            line_number = caller_frame.f_lineno
            return {
                "caller_file": filename,
                "caller_function": function_name,
                "caller_line": str(line_number)
            }
    except (AttributeError, IndexError):
        pass
    finally:
        del frame
    return {}


class LLMServiceBase(ABC):
    def __init__(self, provider: LLMProvider):
        self.provider = provider
        self._client: Optional[AsyncOpenAI] = None

    @abstractmethod
    def create_async_client(self) -> AsyncOpenAI:
        pass

    @abstractmethod
    async def _fetch_completion(
        self,
        messages: List[Dict[str, Any]],
        args: dict | None = None,
        model: str | None = None,
        response_clazz: Type[BaseModel] | None = None
    ) -> Any:
        pass

    async def fetch_completion(
        self,
        messages: List[Dict[str, Any]],
        args: dict | None = None,
        model: str | None = None,
        response_clazz: Type[BaseModel] | Dict | None = None,
        trace: dict | None = None,
        component: str = "rewriter"
    ) -> str:
        if not model:
            raise ValueError("model parameter is required")

        caller_info = _get_caller_info()
        combined_trace = {
            "provider": self.provider.value,
            "component": component,
        }
        if trace:
            combined_trace.update(trace)

        @observe(
            name=f"{caller_info.get('caller_file', 'unknown')}:{caller_info.get('caller_function', 'unknown')}",
            as_type="generation"
        )
        async def observed_fetch():
            response = await self._fetch_completion(messages, args, model, response_clazz)
            content = response.choices[0].message.content
            langfuse = get_client()
            langfuse.update_current_trace(metadata=combined_trace)
            langfuse.update_current_generation(
                input=messages,
                model=model,
                usage_details={
                    "input": response.usage.prompt_tokens,
                    "output": response.usage.completion_tokens,
                    "total": response.usage.total_tokens
                },
                metadata={
                    'args': args or None,
                    # "response_schema": response_clazz or None,
                },
            )

            return content

        result = await observed_fetch()

        return result

    def get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = self.create_async_client()
        return self._client
