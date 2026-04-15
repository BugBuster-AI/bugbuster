"""
Лимиты и флаги окружения для Playwright codegen (draft/repair): токены, trace, лог VLM-рана.
"""
from __future__ import annotations

import os


def _i(name: str, default: int) -> int:
    try:
        val = int(os.getenv(name, str(default)).strip())
        return max(0, val)
    except (TypeError, ValueError):
        return default


def env_bool(name: str, default: bool = True) -> bool:
    v = os.getenv(name, "").strip().lower()
    if not v:
        return default
    return v not in ("0", "false", "no")


# User-message blocks (draft / repair)
MAX_TRACE_BLOCK_CHARS = _i("CODEGEN_MAX_TRACE_BLOCK_CHARS", 14_000)
MAX_GLOBAL_TRACE_CHARS = _i("CODEGEN_MAX_GLOBAL_TRACE_CHARS", 6_000)
MAX_PRIOR_STEPS_CHARS = _i("CODEGEN_MAX_PRIOR_STEPS_CHARS", 6_000)
MAX_PRIOR_JS_CHARS = _i("CODEGEN_MAX_PRIOR_JS_CHARS", 10_000)
MAX_VLM_LOG_CHARS = _i("CODEGEN_MAX_VLM_LOG_CHARS", 8_000)
MAX_VLM_ACTION_BLOCK_CHARS = _i("CODEGEN_MAX_VLM_ACTION_BLOCK_CHARS", 2_000)

# Per-step segment inside trace.zip (before user-message cap)
TRACE_SEGMENT_MAX_CHARS = _i("CODEGEN_MAX_TRACE_SEGMENT_CHARS", 12_000)

# Retrieval: из полного compact trace выбираем строки, похожие на NL/VLM-шаг, и сливаем с маркерным сегментом
CODEGEN_TRACE_RETRIEVAL = env_bool("CODEGEN_TRACE_RETRIEVAL", True)
TRACE_RETRIEVAL_TOP_N = _i("CODEGEN_TRACE_RETRIEVAL_TOP_N", 28)
TRACE_RETRIEVAL_WINDOW = _i("CODEGEN_TRACE_RETRIEVAL_WINDOW", 3)
TRACE_RETRIEVAL_MARKER_BOOST = _i("CODEGEN_TRACE_RETRIEVAL_MARKER_BOOST", 4)

# Global trace summary: head + tail of compact lines from full trace.zip
GLOBAL_TRACE_HEAD_LINES = _i("CODEGEN_VLM_TRACE_SUMMARY_HEAD_LINES", 40)
GLOBAL_TRACE_TAIL_LINES = _i("CODEGEN_VLM_TRACE_SUMMARY_TAIL_LINES", 40)

# Optional MinIO VLM agent log {run_id}/{run_id}.log (по умолчанию off — шум; DOM приоритетнее)
CODEGEN_VLM_RUN_LOG = env_bool("CODEGEN_VLM_RUN_LOG", False)
# Head/tail compact trace (по умолчанию off — освободить бюджет под VLM DOM)
CODEGEN_VLM_TRACE_GLOBAL_SUMMARY = env_bool("CODEGEN_VLM_TRACE_GLOBAL_SUMMARY", False)

# VLM before-step focused DOM в промпте draft/repair
CODEGEN_USE_VLM_STEP_HTML = env_bool("CODEGEN_USE_VLM_STEP_HTML", True)
MAX_VLM_FOCUSED_DOM_PROMPT_CHARS = _i("CODEGEN_MAX_VLM_FOCUSED_DOM_PROMPT_CHARS", 12_000)
# Полный HTML из run_step.dom_before_full — только если нужен доп. контекст (repair)
MAX_VLM_BEFORE_FULL_HTML_CHARS = _i("CODEGEN_MAX_VLM_BEFORE_FULL_HTML_CHARS", 24_000)

# HTML / a11y in llm_prompts (repair) — re-export for single source of truth
MAX_PAGE_HTML_CHARS = _i("CODEGEN_MAX_PAGE_HTML_CHARS", 28_000)
MAX_A11Y_SNAPSHOT_CHARS = _i("CODEGEN_MAX_A11Y_SNAPSHOT_CHARS", 24_000)
