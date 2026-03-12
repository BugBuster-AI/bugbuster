import threading
from typing import Any, Tuple

from agent.models.factory import ModelFactory
from agent.reflection import ReflectionFactory
from core.config import INFERENCE_BASE_URL, INFERENCE_MODEL, REFLECTION_MODEL
from core.model_resolver import resolve_model_url


async def resolve_inference_url(inference_model: str = INFERENCE_MODEL) -> str:
    # Теперь поддерживаем только URL (OpenRouter или локальный vLLM),
    # без GCP instance ID.
    return await resolve_model_url(INFERENCE_BASE_URL)


class InferenceClientRegistry:
    _model_clients: dict[tuple[str, str], Any] = {}
    _reflection_clients: dict[tuple[str, str], Any] = {}
    _lock = threading.Lock()

    @classmethod
    async def get_model_client(cls, model_type: str = INFERENCE_MODEL, inference_url: str | None = None) -> tuple[str, Any]:
        resolved_url = inference_url or await resolve_inference_url(model_type)
        key = (model_type.lower(), resolved_url)

        client = cls._model_clients.get(key)
        if client is not None:
            return resolved_url, client

        with cls._lock:
            client = cls._model_clients.get(key)
            if client is None:
                client = ModelFactory.create_model(model_type, resolved_url)
                cls._model_clients[key] = client
        return resolved_url, client

    @classmethod
    async def get_reflection_client(
        cls,
        reflection_model: str = REFLECTION_MODEL,
        inference_url: str | None = None,
    ) -> tuple[str, Any]:
        resolved_url = inference_url or await resolve_inference_url(INFERENCE_MODEL)
        key = (reflection_model.lower(), resolved_url)

        client = cls._reflection_clients.get(key)
        if client is not None:
            return resolved_url, client

        with cls._lock:
            client = cls._reflection_clients.get(key)
            if client is None:
                client = ReflectionFactory.create_reflection_client(
                    reflection_model, inference_ip=resolved_url
                )
                cls._reflection_clients[key] = client
        return resolved_url, client

    @classmethod
    async def get_clients(
        cls,
        model_type: str = INFERENCE_MODEL,
        reflection_model: str = REFLECTION_MODEL,
    ) -> Tuple[str, Any, Any]:
        inference_url, model_client = await cls.get_model_client(model_type=model_type)
        _, reflection_client = await cls.get_reflection_client(
            reflection_model=reflection_model, inference_url=inference_url
        )
        return inference_url, model_client, reflection_client
