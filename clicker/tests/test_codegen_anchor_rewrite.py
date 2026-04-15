"""Тесты anchor-first: парсинг wait chain и детерминированный rewrite getByTestId → [data-*]."""

from codegen.llm_steps import (
    DATA_ATTR_PRIORITY,
    extract_mcp_waiting_chain,
    extract_wait_chain_anchor_first_segment,
    find_best_data_attr,
    rewrite_js_fragment_get_by_test_id_to_data_attr,
    rewrite_js_fragment_get_by_test_id_to_data_test,
    should_rewrite_get_by_test_id_to_data_attr,
    should_rewrite_get_by_test_id_to_data_test,
)


# ---------------------------------------------------------------------------
# Anchor extraction (unchanged)
# ---------------------------------------------------------------------------
def test_extract_anchor_from_mcp_waiting_line():
    err = (
        "TimeoutError: locator resolved to 0 elements\n"
        "waiting for getByTestId('login-credentials').getByText('locked_out_user')"
    )
    chain = extract_mcp_waiting_chain(err)
    assert chain is not None
    assert "getByTestId('login-credentials')" in chain
    anchor = extract_wait_chain_anchor_first_segment(chain)
    assert anchor == "getByTestId('login-credentials')"


def test_extract_anchor_with_page_prefix_in_chain():
    """Если в логе есть page. — первый сегмент до точки вне кавычек."""
    chain = "page.getByText('Hi').locator('div')"
    assert extract_wait_chain_anchor_first_segment(chain) == "page.getByText('Hi')"


# ---------------------------------------------------------------------------
# Backward-compatible aliases (old names → new implementation)
# ---------------------------------------------------------------------------
def test_should_rewrite_data_test_only_in_html():
    html = '<div data-test="login-credentials">x</div>'
    assert should_rewrite_get_by_test_id_to_data_test("login-credentials", html) is True
    html_both = '<div data-testid="login-credentials" data-test="login-credentials">x</div>'
    assert should_rewrite_get_by_test_id_to_data_test("login-credentials", html_both) is False


def test_rewrite_get_by_test_id_to_data_test_locator():
    html = '<div id="login_credentials" data-test="login-credentials">'
    js = "await page.getByTestId('login-credentials').getByText('u').click();"
    out = rewrite_js_fragment_get_by_test_id_to_data_test(js, html)
    assert "getByTestId('login-credentials')" not in out
    assert 'locator(\'[data-test="login-credentials"]\')' in out
    assert "getByText('u')" in out


# ---------------------------------------------------------------------------
# data-testid present → no rewrite
# ---------------------------------------------------------------------------
def test_no_rewrite_when_data_testid_exists():
    html = '<button data-testid="submit-btn">OK</button>'
    assert find_best_data_attr("submit-btn", html) is None
    assert should_rewrite_get_by_test_id_to_data_attr("submit-btn", html) is False
    js = "await page.getByTestId('submit-btn').click();"
    assert rewrite_js_fragment_get_by_test_id_to_data_attr(js, html) == js


# ---------------------------------------------------------------------------
# Only data-cy → rewrite to [data-cy="…"]
# ---------------------------------------------------------------------------
def test_rewrite_to_data_cy():
    html = '<input data-cy="email-input" type="email">'
    assert find_best_data_attr("email-input", html) == "data-cy"
    js = "await page.getByTestId('email-input').fill(login);"
    out = rewrite_js_fragment_get_by_test_id_to_data_attr(js, html)
    assert 'locator(\'[data-cy="email-input"]\')' in out
    assert "getByTestId" not in out


# ---------------------------------------------------------------------------
# Priority: data-test wins over data-cy when both have same value
# ---------------------------------------------------------------------------
def test_priority_data_test_over_data_cy():
    html = '<div data-cy="card" data-test="card">content</div>'
    assert find_best_data_attr("card", html) == "data-test"
    js = "await page.getByTestId('card').click();"
    out = rewrite_js_fragment_get_by_test_id_to_data_attr(js, html)
    assert 'locator(\'[data-test="card"]\')' in out


# ---------------------------------------------------------------------------
# Priority order constant is correct
# ---------------------------------------------------------------------------
def test_priority_tuple_order():
    assert DATA_ATTR_PRIORITY == (
        "data-testid",
        "data-test",
        "data-cy",
        "data-qa",
        "data-id",
    )


# ---------------------------------------------------------------------------
# Two nodes with same attr name and value at different depths → deeper wins
# ---------------------------------------------------------------------------
def test_deeper_node_preferred():
    html = (
        '<section data-test="section">'
        '  <div data-test="section"><span>inner</span></div>'
        '</section>'
    )
    assert find_best_data_attr("section", html) == "data-test"


# ---------------------------------------------------------------------------
# data-* attr on ancestor only (target has no data-*) → still returns attr
# ---------------------------------------------------------------------------
def test_ancestor_data_attr_found():
    html = '<form data-qa="login-form"><input type="text"><button>Go</button></form>'
    assert find_best_data_attr("login-form", html) == "data-qa"
    js = "await page.getByTestId('login-form').getByRole('button').click();"
    out = rewrite_js_fragment_get_by_test_id_to_data_attr(js, html)
    assert 'locator(\'[data-qa="login-form"]\')' in out
    assert "getByTestId" not in out


# ---------------------------------------------------------------------------
# data-testid on ancestor + data-test on descendant → no rewrite (testid found)
# ---------------------------------------------------------------------------
def test_data_testid_on_ancestor_blocks_rewrite():
    html = (
        '<div data-testid="wrapper">'
        '  <span data-test="wrapper">text</span>'
        '</div>'
    )
    assert find_best_data_attr("wrapper", html) is None


# ---------------------------------------------------------------------------
# Unknown data-* attr not in priority list → falls back lexicographically
# ---------------------------------------------------------------------------
def test_unknown_data_attr_lexicographic():
    html = '<div data-foo="x" data-bar="x">y</div>'
    best = find_best_data_attr("x", html)
    assert best in ("data-bar", "data-foo")
    assert best == "data-bar"


# ---------------------------------------------------------------------------
# Multiple getByTestId in one fragment → each resolved independently
# ---------------------------------------------------------------------------
def test_multiple_get_by_test_id_in_fragment():
    html = (
        '<div data-test="a">x</div>'
        '<div data-cy="b">y</div>'
    )
    js = (
        "await page.getByTestId('a').click();\n"
        "await page.getByTestId('b').fill('hi');"
    )
    out = rewrite_js_fragment_get_by_test_id_to_data_attr(js, html)
    assert 'locator(\'[data-test="a"]\')' in out
    assert 'locator(\'[data-cy="b"]\')' in out
    assert "getByTestId" not in out


# ---------------------------------------------------------------------------
# Empty / missing inputs → safe no-ops
# ---------------------------------------------------------------------------
def test_empty_inputs():
    assert find_best_data_attr("", "<div>x</div>") is None
    assert find_best_data_attr("x", "") is None
    assert rewrite_js_fragment_get_by_test_id_to_data_attr("", "<div>x</div>") == ""
    assert rewrite_js_fragment_get_by_test_id_to_data_attr("code", "") == "code"
