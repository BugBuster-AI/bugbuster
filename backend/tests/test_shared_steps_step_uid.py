"""step_uid для shared_steps.steps (steps_nl_normalization)."""
import copy

from api.services.steps_nl_normalization import (
    assign_step_uids_new_shared_steps,
    ensure_step_uids_on_shared_steps_update,
    ensure_unique_step_uids_in_list,
)


def test_assign_step_uids_new_shared_steps_adds_uid():
    steps = [
        {"type": "action", "value": "click A"},
        {"type": "action", "value": "click B"},
    ]
    assign_step_uids_new_shared_steps(steps)
    assert steps[0].get("step_uid")
    assert steps[1].get("step_uid")
    assert steps[0]["step_uid"] != steps[1]["step_uid"]


def test_assign_step_uids_new_shared_steps_preserves_existing():
    steps = [
        {"type": "action", "value": "x", "step_uid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"},
        {"type": "action", "value": "y"},
    ]
    assign_step_uids_new_shared_steps(steps)
    assert steps[0]["step_uid"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    assert steps[1].get("step_uid")


def test_ensure_unique_step_uids_in_list_fixes_duplicate():
    steps = [
        {"type": "action", "value": "a", "step_uid": "same-uid-0000-0000-0000-000000000001"},
        {"type": "action", "value": "b", "step_uid": "same-uid-0000-0000-0000-000000000001"},
    ]
    ensure_unique_step_uids_in_list(steps)
    assert steps[0]["step_uid"] == "same-uid-0000-0000-0000-000000000001"
    assert steps[1]["step_uid"] != steps[0]["step_uid"]


def test_ensure_step_uids_on_shared_steps_update_merges_by_index():
    old = [
        {"type": "action", "value": "old1", "step_uid": "11111111-1111-1111-1111-111111111111"},
        {"type": "action", "value": "old2", "step_uid": "22222222-2222-2222-2222-222222222222"},
    ]
    new = copy.deepcopy(old)
    new[0]["value"] = "new text 1"
    new[1]["value"] = "new text 2"
    del new[0]["step_uid"]
    del new[1]["step_uid"]
    ensure_step_uids_on_shared_steps_update(old, new)
    assert new[0]["step_uid"] == "11111111-1111-1111-1111-111111111111"
    assert new[1]["step_uid"] == "22222222-2222-2222-2222-222222222222"


def test_ensure_step_uids_on_shared_steps_update_extra_step_gets_uid():
    old = [{"type": "action", "value": "a", "step_uid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"}]
    new = copy.deepcopy(old) + [{"type": "action", "value": "b"}]
    ensure_step_uids_on_shared_steps_update(old, new)
    assert new[0]["step_uid"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    assert new[1].get("step_uid")
