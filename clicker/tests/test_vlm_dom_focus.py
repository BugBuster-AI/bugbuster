"""Unit tests for VLM DOM focused bundle (codegen)."""
import json

from codegen.vlm_dom_focus import build_focused_dom_bundle, focused_dom_bundle_to_prompt_text


def test_build_focused_dom_finds_data_testid():
    html = """
    <html><body>
    <div data-testid="add-to-cart" class="btn">Add</div>
    <button id="x">Ok</button>
    </body></html>
    """
    b = build_focused_dom_bundle(html, url="https://ex.com/", max_candidates=20, max_snippet_chars=5000)
    assert b["url"] == "https://ex.com/"
    assert len(b["candidates"]) >= 1
    tags = [c["tag"] for c in b["candidates"]]
    assert "div" in tags or "button" in tags
    assert any(
        "data-testid" in c.get("attrs", {}) and c["attrs"]["data-testid"] == "add-to-cart"
        for c in b["candidates"]
    )


def test_focused_dom_deterministic_order():
    html = """
    <a data-testid="z">1</a>
    <a data-testid="a">2</a>
    """
    b1 = build_focused_dom_bundle(html, max_candidates=10)
    b2 = build_focused_dom_bundle(html, max_candidates=10)
    assert json.dumps(b1["candidates"], sort_keys=True) == json.dumps(b2["candidates"], sort_keys=True)


def test_focused_dom_bundle_to_prompt_text_truncates():
    b = build_focused_dom_bundle("<div data-testid=x>" + "y" * 20000 + "</div>", max_snippet_chars=100)
    t = focused_dom_bundle_to_prompt_text(b, max_chars=500)
    assert len(t) <= 550
    assert "truncated" in t or len(t) <= 500
