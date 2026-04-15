"""Точечный repair expected_result: парсинг Locator из ошибки MCP и замена только совпадающих строк."""

import pytest

from codegen.llm_steps import (
    extract_failed_locator_inner_from_playwright_error,
    extract_locator_chain_literals_from_playwright_error,
    find_expected_result_line_indices_matching_locator_chain,
    find_expected_result_line_indices_matching_locator_inner,
    repair_expected_result_fragment_maybe_targeted,
)


def test_extract_failed_locator_from_locator_line():
    err = """### Error
Error: expect(locator).not.toHaveText(expected) failed

Locator: locator('//div[@data-test="cart-contents-container"]//div[@class="cart_list"]')
Expected: not "Sauce Labs Bike Light"
"""
    inner = extract_failed_locator_inner_from_playwright_error(err)
    assert inner is not None
    assert "cart-contents-container" in inner
    assert inner.startswith("//div")


def test_extract_failed_locator_from_waiting_for_line():
    err = (
        'Call log:\n  - Expect "to.have.text" with timeout 5000ms\n'
        "  - waiting for locator('xpath=//button[@id=\"ok\"]')"
    )
    inner = extract_failed_locator_inner_from_playwright_error(err)
    assert inner == 'xpath=//button[@id="ok"]'


def test_find_line_indices_matching_inner():
    inner = "xpath=//bad"
    prev = """await expect(page.locator('xpath=//bad')).toBeVisible();
await expect(page.locator('xpath=//bad')).toContainText('a');
await expect(page.locator('xpath=//ok')).toBeVisible();"""
    idx = find_expected_result_line_indices_matching_locator_inner(prev, inner)
    assert idx == [0, 1]


def test_extract_chain_literals_from_trace_like_error():
    err = """### Error
Error: expect(locator).toBeHidden() failed

Locator:  locator('[data-test="cart-list"]').locator('text=QTY').locator('../following-sibling::div')
Expected: hidden
Received: visible
"""
    t = extract_locator_chain_literals_from_playwright_error(err)
    assert t is not None
    assert len(t) == 3
    assert 'cart-list' in t[0]
    assert t[1] == "text=QTY"
    assert "following-sibling" in t[2]


def test_chain_match_only_one_line_among_similar_cart_lines():
    err = (
        'Locator: locator(\'[data-test="cart-list"]\').locator(\'text=QTY\').locator(\'../following-sibling::div\')\n'
    )
    literals = extract_locator_chain_literals_from_playwright_error(err)
    assert literals is not None
    prev = """
await expect(page.locator('[data-test="cart-list"]').locator('text=QTY')).toBeVisible();
await expect(page.locator('[data-test="cart-list"]').locator('text=QTY').locator('xpath=../following-sibling::div')).toBeHidden({ message: 'Cart item row should be gone after removal' });
await expect(page.locator('[data-test="cart-list"]').locator('text=Subtotal')).toBeVisible();
""".strip()
    idx = find_expected_result_line_indices_matching_locator_chain(prev, literals)
    assert idx == [1]


@pytest.mark.asyncio
async def test_maybe_targeted_repairs_only_matching_lines(monkeypatch):
    calls: list[str] = []

    async def fake_single(**kwargs):
        calls.append(kwargs["original_assertion_line"])
        return "await expect(page.locator('xpath=//fixed')).toBeVisible();"

    monkeypatch.setattr(
        "codegen.llm_steps.repair_expected_result_single_assertion_line",
        fake_single,
    )

    err = "Error: expect failed\n\nLocator: locator('xpath=//bad')"
    prev = """await expect(page.locator('xpath=//bad')).toBeVisible();
await expect(page.locator('xpath=//bad')).toContainText('a');
await expect(page.locator('xpath=//ok')).toBeVisible();"""

    out = await repair_expected_result_fragment_maybe_targeted(
        step_uid="test-uid",
        nl="expect cart",
        base_url="https://example.com",
        viewport_w=1280,
        viewport_h=720,
        before_b64=None,
        after_b64=None,
        failure_screenshot_b64=None,
        previous_js=prev,
        playwright_error=err,
        repair_attempt=2,
        max_validation_attempts=5,
        prior_failed_wait_chains=[],
        accessibility_snapshot=None,
        langchain_callbacks=None,
        vlm_coords=None,
        trace_hint=None,
        anchor_must_change=False,
        anchor_first_hint=None,
        mcp_page_html=None,
        vlm_action="expected_result",
    )

    # Один и тот же inner на двух строках; чиним только первую (порядок прогона Playwright).
    assert len(calls) == 1
    lines = out.splitlines()
    assert lines[0] == "await expect(page.locator('xpath=//fixed')).toBeVisible();"
    assert lines[1] == "await expect(page.locator('xpath=//bad')).toContainText('a');"
    assert lines[2] == "await expect(page.locator('xpath=//ok')).toBeVisible();"


@pytest.mark.asyncio
async def test_maybe_targeted_falls_back_to_full_when_locator_not_in_fragment(monkeypatch):
    full_called = {"n": 0}

    async def fake_full(**kwargs):
        full_called["n"] += 1
        return "FULL_FRAGMENT"

    monkeypatch.setattr(
        "codegen.llm_steps.repair_action_fragment",
        fake_full,
    )

    err = "Locator: locator('xpath=//only-in-error-not-in-code')"
    prev = "await expect(page.locator('xpath=//other')).toBeVisible();"

    out = await repair_expected_result_fragment_maybe_targeted(
        step_uid="u",
        nl="x",
        base_url="https://x.test",
        viewport_w=1280,
        viewport_h=720,
        before_b64=None,
        after_b64=None,
        failure_screenshot_b64=None,
        previous_js=prev,
        playwright_error=err,
        repair_attempt=2,
        max_validation_attempts=5,
        prior_failed_wait_chains=[],
        accessibility_snapshot=None,
        langchain_callbacks=None,
        vlm_coords=None,
        trace_hint=None,
        anchor_must_change=False,
        anchor_first_hint=None,
        mcp_page_html=None,
        vlm_action=None,
    )

    assert full_called["n"] == 1
    assert out == "FULL_FRAGMENT"


def test_normalize_single_assertion_js_fragment_helper():
    from codegen.llm_steps import _normalize_single_assertion_js_fragment

    assert (
        _normalize_single_assertion_js_fragment("await expect(a).toBeVisible();")
        == "await expect(a).toBeVisible();"
    )
    assert (
        _normalize_single_assertion_js_fragment("  await expect(x).toBeVisible()  \n")
        == "await expect(x).toBeVisible();"
    )
