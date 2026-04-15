"""Viewport (browser resolution) from test case environment.

Primary source: ``case.environment.resolution`` — resolution of the Environment linked to the
case via ``environment_id``, embedded in ``current_case_version`` at run time by the backend.

Fallback when environment or resolution is missing/invalid: 1920×1080 (matches backend
:class:`Resolution` defaults in ``backend/schemas.py``).
"""
from __future__ import annotations

from typing import Any, Tuple

DEFAULT_VIEWPORT_WIDTH = 1920
DEFAULT_VIEWPORT_HEIGHT = 1080


def _parse_resolution_dict(res: Any) -> Tuple[int, int] | None:
    if not isinstance(res, dict):
        return None
    try:
        w = int(res.get("width", DEFAULT_VIEWPORT_WIDTH))
        h = int(res.get("height", DEFAULT_VIEWPORT_HEIGHT))
    except (TypeError, ValueError):
        return None
    if w <= 0 or h <= 0:
        return None
    return w, h


def viewport_from_environment(env: Any) -> Tuple[int, int]:
    """Resolve width/height from an environment payload (dict from JSON or pydantic-like object)."""
    if env is None:
        return DEFAULT_VIEWPORT_WIDTH, DEFAULT_VIEWPORT_HEIGHT
    if isinstance(env, dict):
        res = env.get("resolution")
        parsed = _parse_resolution_dict(res)
        if parsed is not None:
            return parsed
        return DEFAULT_VIEWPORT_WIDTH, DEFAULT_VIEWPORT_HEIGHT
    res = getattr(env, "resolution", None)
    if res is not None and hasattr(res, "width") and hasattr(res, "height"):
        try:
            w, h = int(res.width), int(res.height)
            if w > 0 and h > 0:
                return w, h
        except (TypeError, ValueError):
            pass
    return DEFAULT_VIEWPORT_WIDTH, DEFAULT_VIEWPORT_HEIGHT


def viewport_for_case(case: dict, *, environment: Any = None) -> Tuple[int, int]:
    """Viewport for Code runs and codegen validation — same rules as test case Environment.

    Prefers ``case["environment"]`` when it is a dict (snapshot from backend); otherwise uses
    ``environment`` (e.g. worker kwargs when the case dict has no embedded environment).
    """
    ce = case.get("environment")
    env = ce if isinstance(ce, dict) else environment
    return viewport_from_environment(env)
