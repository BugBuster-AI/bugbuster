from typing import Optional

from .anthropic_service import AnthropicService
from .base import LLMProvider, LLMServiceBase
from .google_service import GoogleService
from .openai_service import OpenAIService
from .vllm_service import VLLMService


def create_llm_service(
    provider: LLMProvider,
    api_key: str,
    base_url: Optional[str] = None
) -> LLMServiceBase:
    if provider == LLMProvider.OPENAI:
        return OpenAIService(api_key, base_url)
    elif provider == LLMProvider.VLLM:
        return VLLMService(api_key, base_url)
    elif provider == LLMProvider.GOOGLE:
        return GoogleService(api_key, base_url)
    elif provider == LLMProvider.ANTHROPIC:
        return AnthropicService(api_key, base_url)
    else:
        raise ValueError(f"Unsupported provider: {provider}")