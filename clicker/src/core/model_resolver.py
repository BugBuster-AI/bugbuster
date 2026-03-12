from core.config import logger


async def resolve_model_url(url: str) -> str:
    """
    Resolve and normalize a model URL.

    Поддерживаются только HTTP(S)-URL (OpenRouter, локальный vLLM и т.п.).
    Любые другие форматы (например, GCP instance ID) больше не поддерживаются.
    """
    if not url:
        raise ValueError("Model URL is empty")

    value = url.strip()
    if not value:
        raise ValueError("Model URL is empty")

    if value.startswith(("http://", "https://")):
        return value.rstrip("/")

    raise ValueError(
        f"Unrecognized model destination: '{value}'. Expected an HTTP(S) URL."
    )
