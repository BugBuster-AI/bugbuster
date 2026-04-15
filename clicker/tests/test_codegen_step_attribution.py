"""Сопоставление ошибки Playwright с блоком // step_uid: в полном JS сценария."""
from codegen.llm_steps import infer_step_uid_for_playwright_timeout


def test_infer_timeout_uid_finds_earlier_step():
    script = """
  // step_uid:aaaa
  await page.locator('[data-test="add-to-cart-x"]').click();
  // step_uid:bbbb
  await page.locator('a[data-test="shopping-cart-link"]').click();
"""
    err = """TimeoutError: locator.click: Timeout 5000ms exceeded.
Call log:
  - waiting for locator('[data-test="add-to-cart-x"]')"""
    assert infer_step_uid_for_playwright_timeout(full_script=script, playwright_error=err) == "aaaa"


def test_infer_timeout_uid_same_as_current():
    script = """
  // step_uid:aaaa
  await page.locator('button').click();
  // step_uid:bbbb
  await page.locator('[data-test="only-here"]').click();
"""
    err = 'waiting for locator(\'[data-test="only-here"]\')'
    assert infer_step_uid_for_playwright_timeout(full_script=script, playwright_error=err) == "bbbb"


def test_infer_timeout_empty_error():
    assert infer_step_uid_for_playwright_timeout(full_script="x", playwright_error="") is None
