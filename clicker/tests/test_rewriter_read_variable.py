from pydantic import ValidationError

from agent.rewriter.pydantic_schemas import ActionPlan, RewriterActionPlan


def test_action_plan_accepts_read_with_storage_key_without_braces():
    payload = {
        "actions": [
            {
                "action_type": "READ",
                "instruction": "Скопируй текст кнопки в переменную {{btn_text}}",
                "storage_key": "btn_text",
            }
        ]
    }

    plan = RewriterActionPlan.model_validate(payload)
    assert plan.actions[0].action_type == "READ"
    assert plan.actions[0].storage_key == "btn_text"


def test_rewriter_action_plan_rejects_paste_action():
    payload = {
        "actions": [
            {
                "action_type": "PASTE",
                "element_description": "поле ввода кода",
                "storage_key": "confirmation_code",
            }
        ]
    }

    try:
        RewriterActionPlan.model_validate(payload)
    except ValidationError:
        return

    raise AssertionError("PASTE action must be rejected by RewriterActionPlan")


def test_legacy_action_plan_accepts_paste_action():
    payload = {
        "actions": [
            {
                "action_type": "PASTE",
                "element_description": "поле ввода кода",
                "storage_key": "confirmation_code",
            }
        ]
    }

    plan = ActionPlan.model_validate(payload)
    assert plan.actions[0].action_type == "PASTE"
