"""Тесты normalize_playwright_await_fragment и dedupe_const_declarations."""

from codegen.js_fragment_await import dedupe_const_declarations, normalize_playwright_await_fragment


def test_adds_await_page_goto():
    src = "page.goto('https://example.com');"
    out = normalize_playwright_await_fragment(src)
    assert "await page.goto" in out


def test_adds_await_chain_click():
    src = "page.getByRole('button', { name: 'OK' }).click();"
    out = normalize_playwright_await_fragment(src)
    assert out.strip().startswith("await ")


def test_preserves_existing_await():
    src = "await page.click('text=Hi');"
    out = normalize_playwright_await_fragment(src)
    assert out == src


def test_const_rhs_gets_await():
    src = "const x = page.locator('#a').click();"
    out = normalize_playwright_await_fragment(src)
    assert "const x = await " in out.replace("\n", " ")


def test_skips_comments():
    src = "// page.click('x');\npage.fill('#i', 'v');"
    out = normalize_playwright_await_fragment(src)
    lines = out.splitlines()
    assert lines[0].strip().startswith("//")
    assert "await page.fill" in lines[1]


def test_dedupe_two_const_same_line_after_semicolon():
    """Второй `const text` после `;` не матчится построчным _BINDING — снимаем через постпроход."""
    prior = ""
    frag = "const text = await a(); const text = await b();"
    out = dedupe_const_declarations(prior, frag)
    assert "const text = await a();" in out
    assert "const text = await b()" not in out
    assert "text = await b()" in out


def test_dedupe_second_const_after_preamble_extra_declared():
    prior = ""
    frag = "const text = await x();"
    out = dedupe_const_declarations(prior, frag, extra_declared={"text"})
    assert out.strip() == "text = await x();"


def test_multiline_fragment():
    src = "page.goto('https://example.com');\npage.click('#btn');"
    out = normalize_playwright_await_fragment(src)
    lines = out.strip().splitlines()
    assert "await page.goto" in lines[0]
    assert "await page.click" in lines[1]


def test_nested_calls():
    src = "page.locator('#a').locator('#b').click();"
    out = normalize_playwright_await_fragment(src)
    assert out.strip().startswith("await ")
    assert out.count("await") == 1


def test_string_containing_page_not_awaited():
    src = "console.log('page.click is a method');"
    out = normalize_playwright_await_fragment(src)
    assert "await" not in out
