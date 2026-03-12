import pytest
from data.scroll_sops import scroll_sops
from utils import sop_validation
from rich import print
from time import time
import asyncio

@pytest.mark.parametrize("sop", scroll_sops)
def test_scroll_sop_validation(sop):
    start_time = time()

    res = asyncio.run(sop_validation(sop["sop"]))
    print(res)
    assert res["is_valid"]
    action_types = [action["action_type"] for action in res["action_plan"]]
    assert action_types == sop["expected_actions"], f"Expected action types: {sop['expected_actions']}, Generated action types: {action_types}"
    for i, (expected, generated) in enumerate(zip(sop["expected_fields"], res["action_plan"])):
        generated_fields = {key for key, value in generated.items() if value is not None}
        assert expected == generated_fields, f"Step {i} - Expected fields: {expected}, Generated fields: {generated_fields}"
        
    print(f"Time taken: {time() - start_time:.2f} seconds")

# def test_invalid_sops():
    