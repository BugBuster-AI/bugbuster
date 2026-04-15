"""Unit tests for VLM Playwright trace excerpt segmentation (codegen)."""
import io
import zipfile

from agent.trace_step_marker import TRACE_STEP_UID_PREFIX
from codegen.vlm_trace_excerpt import (
    _compact_lines_indexed,
    _read_trace_jsonl,
    refine_trace_excerpt_for_step,
    segment_trace_for_flat,
)


def _make_trace_zip_bytes(lines: list[str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("trace.trace", "\n".join(lines) + "\n")
    return buf.getvalue()


def test_compact_trace_extracts_api_lines():
    raw = [
        '{"type":"before","metadata":{"apiName":"goto","params":{"url":"https://example.com"}}}',
        '{"noise":true}',
        '{"type":"before","metadata":{"apiName":"click","params":{"selector":"text=Login"}}}',
    ]
    z = _make_trace_zip_bytes(raw)
    entries = _read_trace_jsonl(z)
    out = _compact_lines_indexed(entries)
    assert len(out) == 2
    assert "goto" in out[0][1]
    assert "click" in out[1][1]


def test_segment_maps_step_uids_proportional_fallback():
    flat = [
        {"kind": "expected_result", "step_uid": "e1"},
        {"kind": "action", "step_uid": "a1"},
        {"kind": "action", "step_uid": "a2"},
    ]
    raw = [
        '{"type":"before","metadata":{"apiName":"fill","params":{"text":"u"}}}',
        '{"type":"before","metadata":{"apiName":"fill","params":{"text":"v"}}}',
        '{"type":"before","metadata":{"apiName":"click","params":{}}}',
        '{"type":"before","metadata":{"apiName":"press","params":{}}}',
    ]
    z = _make_trace_zip_bytes(raw)
    seg, _, _ = segment_trace_for_flat(z, flat)
    assert set(seg.keys()) == {"a1", "a2"}
    assert "fill" in seg["a1"]
    assert "press" in seg["a2"] or "click" in seg["a2"]


def test_refine_adds_tokens_from_outside_proportional_segment():
    """Retrieval подтягивает строки по токенам NL из всего compact trace, не только из сегмента."""
    flat = [
        {"kind": "action", "step_uid": "a1"},
        {"kind": "action", "step_uid": "a2"},
    ]
    raw = [
        '{"type":"before","metadata":{"apiName":"a","params":{}}}',
        '{"type":"before","metadata":{"apiName":"b","params":{}}}',
        '{"type":"before","metadata":{"apiName":"c","params":{}}}',
        '{"type":"before","metadata":{"apiName":"d","params":{}}}',
        '{"type":"before","metadata":{"apiName":"e","params":{}}}',
        '{"type":"before","metadata":{"apiName":"fill","params":{"text":"Banana"}}}',
    ]
    z = _make_trace_zip_bytes(raw)
    seg, compact, bounds = segment_trace_for_flat(z, flat)
    base = seg["a1"]
    assert "Banana" not in base
    refined = refine_trace_excerpt_for_step(
        "Type Banana into field",
        None,
        base,
        compact,
        bounds.get("a1"),
    )
    assert "Banana" in refined


def test_segment_by_step_uid_markers():
    """Границы по console-маркерам [BB_STEP_UID] между шагами."""
    flat = [
        {"kind": "action", "step_uid": "a1"},
        {"kind": "action", "step_uid": "a2"},
    ]
    m1 = f'{{"console":{{"text":"{TRACE_STEP_UID_PREFIX}a1"}}}}'
    m2 = f'{{"console":{{"text":"{TRACE_STEP_UID_PREFIX}a2"}}}}'
    raw = [
        '{"type":"before","metadata":{"apiName":"goto","params":{}}}',
        m1,
        '{"type":"before","metadata":{"apiName":"fill","params":{"text":"only_a1"}}}',
        m2,
        '{"type":"before","metadata":{"apiName":"click","params":{}}}',
    ]
    z = _make_trace_zip_bytes(raw)
    seg, compact, bounds = segment_trace_for_flat(z, flat)
    assert set(seg.keys()) == {"a1", "a2"}
    assert "only_a1" in seg["a1"]
    assert "fill" in seg["a1"]
    assert "click" in seg["a2"]
    assert "goto" not in seg["a1"] and "goto" not in seg["a2"]
