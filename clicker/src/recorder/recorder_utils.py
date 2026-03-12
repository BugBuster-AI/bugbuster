
import os
import time
from pathlib import Path
from typing import Any, List

import instructor
import openai  # TODO: rewrite to Async
import requests

from core.config import INFERENCE_API_KEY, INFERENCE_BASE_URL, logger


def download_image(url: str, folder: str, filename: str) -> str:
    Path(folder).mkdir(parents=True, exist_ok=True)

    file_path = Path(folder) / filename
    response = requests.get(url)

    if response.status_code == 200:
        with open(file_path, "wb") as file:
            file.write(response.content)
        logger.info(f"Image successfully downloaded to {file_path}")
    else:
        logger.info(f"Failed to download image. Status code: {response.status_code}")

    return str(file_path)


def _fetch_openai_structured_completion(
    messages: List[Any], attempt: int = 1, **kwargs: Any
):
    """
    Вспомогательная функция для получения структурированного ответа от модели.

    Всегда использует единый inference-ендпойнт:
    INFERENCE_BASE_URL / INFERENCE_API_KEY (OpenRouter или локальный vLLM).
    """
    client = instructor.from_openai(
        openai.OpenAI(api_key=INFERENCE_API_KEY, base_url=INFERENCE_BASE_URL)
    )
    try:
        # TODO: унифицировать использование response_format и kwargs
        response_model = kwargs.get("response_format")
        if "response_format" in kwargs:
            del kwargs["response_format"]

        model, response = client.chat.completions.create_with_completion(
            model=kwargs["model"],
            response_model=response_model,
            messages=messages,
            # **kwargs  # опционально, если нужно прокидывать остальные аргументы
        )
        usage = response.usage
    except openai.RateLimitError as e:
        if attempt <= 3:
            logger.info("Rate limit exceeded -- waiting 10 sec before retrying")
            time.sleep(10)
            return _fetch_openai_structured_completion(messages, attempt=attempt+1, **kwargs)
        else:
            logger.info("Rate limit exceeded after 3 attempts")
            raise e
    except openai.BadRequestError as e:
        if attempt <= 3:
            logger.info(f"Bad request error -- waiting 10 seconds before retrying (Attempt {attempt}/10)")
            time.sleep(10)
            return _fetch_openai_structured_completion(messages, attempt=attempt+1, **kwargs)
        else:
            logger.info(f"Error in OpenAI API call after 10 attempts: {e}")
            raise e
    except Exception as e:
        logger.info(f"Error in OpenAI API call: {e}")
        raise e
    return model, usage