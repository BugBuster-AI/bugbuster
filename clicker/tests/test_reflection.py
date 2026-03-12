import os

import pytest
from agent.reflection import verify_screenshot
from data.reflection_sops import reflections
from data.reflection_sop_ru import reflections as reflections_ru
from data.reflection_sop_en import reflections as reflections_en
from data.reflection_sop_ar import reflections as reflections_ar
from rich import print

test_reflections = reflections_ru# + reflections[-2:]

REFLECTION_MODEL = "claude_35" #tars_v15

@pytest.mark.parametrize("reflection", test_reflections)
def test_reflection(reflection):
    print(os.path.exists(reflection["path"]))
    path = os.path.join("..", reflection["path"])
    result = verify_screenshot(REFLECTION_MODEL, path, reflection["prompt"])
    print(result)
    assert result.verification_passed == reflection["expected_result"]

    assert result.verification_passed == reflection["expected_result"]