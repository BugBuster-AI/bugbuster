import json
import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s (%(filename)s:%(funcName)s:%(lineno)d) [%(levelname)s] - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("clicker")
logger.setLevel(logging.INFO)
logging.getLogger("urllib3").setLevel(logging.ERROR)


UVICORN_PORT = int(os.getenv("UVICORN_PORT", "7660"))


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_PROVIDER = os.getenv("OPENROUTER_PROVIDER", "alibaba")
OPENROUTER_ALLOW_FALLBACKS = bool(int(os.getenv("OPENROUTER_ALLOW_FALLBACKS", "0")))
OPENROUTER_PROVIDER_EXTRA_BODY_RAW = os.getenv(
    "OPENROUTER_PROVIDER_EXTRA_BODY", ""
).strip()

if OPENROUTER_PROVIDER_EXTRA_BODY_RAW:
    try:
        OPENROUTER_PROVIDER_EXTRA_BODY = json.loads(OPENROUTER_PROVIDER_EXTRA_BODY_RAW)
    except Exception:
        logger.warning(
            "Invalid OPENROUTER_PROVIDER_EXTRA_BODY JSON, fallback to OPENROUTER_PROVIDER variables"
        )
        OPENROUTER_PROVIDER_EXTRA_BODY = {
            "provider": {
                "order": [OPENROUTER_PROVIDER],
                "allow_fallbacks": OPENROUTER_ALLOW_FALLBACKS,
            }
        }
else:
    OPENROUTER_PROVIDER_EXTRA_BODY = {
        "provider": {
            "order": [OPENROUTER_PROVIDER],
            "allow_fallbacks": OPENROUTER_ALLOW_FALLBACKS,
        }
    }

# CLICK model configuration (qwen3_vl implementation in agent/models/qwen3_vl.py)
# Legacy variables (kept for backward compatibility)
QWEN3_VL_BASE_URL = os.getenv("QWEN3_VL_BASE_URL", os.getenv("QWEN3_VL_IP", ""))
QWEN3_VL_API_KEY = os.getenv("QWEN3_VL_API_KEY", OPENROUTER_API_KEY)
QWEN3_VL_MODEL_NAME = os.getenv("QWEN3_VL_MODEL_NAME", "qwen/qwen3-vl-8b-instruct")
INFERENCE_SERVER_URL = os.getenv("INFERENCE_SERVER_URL", "").strip()

# Unified inference configuration (new variables take priority over legacy ones)
INFERENCE_BASE_URL = os.getenv(
    "INFERENCE_BASE_URL", INFERENCE_SERVER_URL or QWEN3_VL_BASE_URL or ""
)
INFERENCE_API_KEY = os.getenv("INFERENCE_API_KEY", QWEN3_VL_API_KEY)
INFERENCE_MODEL_NAME = os.getenv("INFERENCE_MODEL_NAME", QWEN3_VL_MODEL_NAME)

REFLECTION_MODEL = os.getenv(
    "REFLECTION_MODEL", "qwen3_vl"
)  # claude_35 or tars_v15 or qwen3_vl
INFERENCE_MODEL = os.getenv("INFERENCE_MODEL", "qwen3_vl")


LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://dlserver:3300")

LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")

LANGFUSE_REWRITER_PUBLIC_KEY = os.getenv("LANGFUSE_REWRITER_PUBLIC_KEY", "")
LANGFUSE_REWRITER_SECRET_KEY = os.getenv("LANGFUSE_REWRITER_SECRET_KEY", "")

LANGFUSE_RECORDER_PUBLIC_KEY = os.getenv("LANGFUSE_RECORDER_PUBLIC_KEY", "")
LANGFUSE_RECORDER_SECRET_KEY = os.getenv("LANGFUSE_RECORDER_SECRET_KEY", "")

LOCALHOST_DISABLED = int(
    os.getenv("LOCALHOST_DISABLED", "0")
)  # запрет вне контура таких url

PROXY_ENABLED = int(os.getenv("PROXY_ENABLED", "0"))


SOP_REWRITER_API_KEY = os.getenv("SOP_REWRITER_API_KEY", OPENROUTER_API_KEY)
SOP_REWRITER_MODEL_NAME = os.getenv(
    "SOP_REWRITER_MODEL_NAME", "qwen/qwen3-next-80b-a3b-instruct"
)
SOP_REWRITER_PROVIDER = os.getenv("SOP_REWRITER_PROVIDER", "openai")
SOP_REWRITER_BASE_URL = os.getenv("SOP_REWRITER_BASE_URL", "")
