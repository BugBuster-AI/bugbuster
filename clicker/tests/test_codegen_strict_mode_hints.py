"""Tests for strict mode violation hint extraction (Playwright codegen repair)."""
from codegen.llm_prompts import strict_mode_hints_block
from codegen.playwright_strict_mode_hints import format_strict_mode_hints_from_playwright_error


def test_strict_mode_extracts_resolved_to_and_candidates():
    err = """### Error
Error: expect(locator).toHaveText(expected) failed

Locator: locator('text=Браузер').locator('../following-sibling::div[1]')
Expected: "Google Chrome 147.0.7727.55 (WebKit 537.36)"
Error: strict mode violation: locator('text=Браузер').locator('../following-sibling::div[1]') resolved to 4 elements:
    1) <div class="general-info__parameter-value">Google Chrome 147.0.7727.55 (WebKit 537.36)</div> aka getByText('Google Chrome 147.0.7727.55 (').first()
    2) <div class="list-info__item">…</div> aka getByText('Операционная система: Windows')

Call log:
  - Expect "to.have.text" with timeout 5000ms
"""
    out = format_strict_mode_hints_from_playwright_error(err)
    assert out is not None
    assert "strict_mode_violation=true" in out
    assert "resolved_to=4" in out
    assert "general-info__parameter-value" in out
    assert "aka getByText" in out
    wrapped = strict_mode_hints_block(out)
    assert "Strict mode violation hints extracted from the error (use these first):" in wrapped


def test_non_strict_error_returns_none():
    assert format_strict_mode_hints_from_playwright_error("Timeout 5000ms waiting for locator('foo')") is None


def test_strict_without_resolved_to_returns_none():
    assert format_strict_mode_hints_from_playwright_error("strict mode violation: something else") is None
