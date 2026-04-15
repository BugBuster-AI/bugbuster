"""Tests for viewport resolution from test case environment."""
from codegen.case_viewport import (
    DEFAULT_VIEWPORT_HEIGHT,
    DEFAULT_VIEWPORT_WIDTH,
    viewport_for_case,
    viewport_from_environment,
)


def test_viewport_from_environment_dict_resolution():
    assert viewport_from_environment(
        {"resolution": {"width": 1440, "height": 900}}
    ) == (1440, 900)


def test_viewport_for_case_prefers_embedded_environment_dict():
    case = {
        "environment": {"resolution": {"width": 1280, "height": 720}},
    }
    assert viewport_for_case(case, environment={"resolution": {"width": 1920, "height": 1080}}) == (
        1280,
        720,
    )


def test_viewport_for_case_uses_kwarg_when_case_has_no_dict_environment():
    case = {}
    env = {"resolution": {"width": 1600, "height": 900}}
    assert viewport_for_case(case, environment=env) == (1600, 900)


def test_viewport_for_case_fallback_when_missing():
    case = {}
    assert viewport_for_case(case) == (DEFAULT_VIEWPORT_WIDTH, DEFAULT_VIEWPORT_HEIGHT)
