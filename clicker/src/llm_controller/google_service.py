from typing import Any, Dict, List, Type

from openai import AsyncOpenAI
from pydantic import BaseModel

from core.config import logger

from .base import LLMProvider, LLMServiceBase


class GoogleService(LLMServiceBase):
    def __init__(self, api_key: str, base_url: str):
        super().__init__(LLMProvider.GOOGLE)
        self.api_key = api_key
        self.base_url = base_url

    def create_async_client(self) -> AsyncOpenAI:
        return AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    async def _fetch_completion(
        self,
        messages: List[Dict[str, Any]],
        args: dict | None = None,
        model: str | None = None,
        response_clazz: Type[BaseModel] | None = None
    ) -> Any:
        if not model:
            raise ValueError("model parameter is required")

        client = self.get_client()

        completion_kwargs = {
            "model": model,
            "messages": messages,
            "temperature": 0
        }

        if args:
            filtered_args = {k: v for k, v in args.items() if k != "extra_body"}
            completion_kwargs.update(filtered_args)

        try:
            if response_clazz:
                if isinstance(response_clazz, type) and issubclass(response_clazz, BaseModel):
                    name = response_clazz.__name__
                    response_schema = response_clazz.model_json_schema()
                else:
                    name = "response_schema"
                    response_schema = response_clazz
                response = await client.chat.completions.create( # type: ignore
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": name,
                            "schema": response_schema,
                            "strict": False,
                        },
                    },
                    **completion_kwargs
                )
            else:
                response = await client.chat.completions.create(
                    **completion_kwargs
                )
            logger.debug(f"Google API call successful for model: {model}")
            return response

        except Exception as e:
            logger.error(f"Google API call failed: {str(e)}")
            raise