"""effective_step_uid: run_steps.step_uid overrides flatten idx_N."""
from codegen.case_steps import effective_step_uid, flatten_case_with_run_indices


def test_effective_step_uid_prefers_run_step():
    item = {
        "step_uid": "idx_0",
        "run_step": {"step_uid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "action": "CLICK"},
        "kind": "action",
        "run_index": 0,
    }
    assert effective_step_uid(item) == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def test_effective_step_uid_falls_back_to_flat():
    item = {
        "step_uid": "idx_2",
        "run_step": {},
        "kind": "action",
        "run_index": 2,
    }
    assert effective_step_uid(item) == "idx_2"


def test_effective_step_uid_empty_run_step_uses_flat():
    item = {
        "step_uid": "real-uid-1111",
        "run_step": {"action": "CLICK"},
        "kind": "action",
        "run_index": 0,
    }
    assert effective_step_uid(item) == "real-uid-1111"


def test_flatten_then_effective_with_run_step():
    case = {
        "before_browser_start": [],
        "before_steps": [{"type": "action", "value": "x", "step_uid": "case-only"}],
        "steps": [],
        "after_steps": [],
    }
    flat = flatten_case_with_run_indices(case)
    flat[0]["run_step"] = {"step_uid": "from-db-2222", "index_step": 0}
    flat[0]["step_uid"] = effective_step_uid(flat[0])
    assert flat[0]["step_uid"] == "from-db-2222"
