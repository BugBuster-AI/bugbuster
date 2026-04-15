"""Unit tests for desktop Chrome UA formatting (no browser launch)."""

from codegen.effective_browser import format_desktop_chrome_user_agent


def test_format_desktop_chrome_user_agent_from_semver_string():
    ua = format_desktop_chrome_user_agent("131.0.6778.33")
    assert ua is not None
    assert "Chrome/131.0.6778.33" in ua
    assert "HeadlessChrome" not in ua
    assert "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" in ua


def test_format_desktop_chrome_user_agent_from_chrome_prefix():
    ua = format_desktop_chrome_user_agent("Chrome/130.0.6723.58")
    assert ua is not None
    assert "Chrome/130.0.6723.58" in ua


def test_format_desktop_chrome_user_agent_empty_returns_none():
    assert format_desktop_chrome_user_agent("") is None
    assert format_desktop_chrome_user_agent("   ") is None
