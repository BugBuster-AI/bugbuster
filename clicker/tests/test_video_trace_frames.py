"""Тесты find_matching_screenshots: последний кадр после after.endTime не отбрасывается."""

import os
import sys

from browser_actions.extract_video_from_trace import (
    LAST_SCREENCAST_FRAME_TAIL_SEC as CLICKER_TAIL,
    find_matching_screenshots as find_matching_screenshots_clicker,
)

_VG_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "infra", "video-generate-service"))
_added_vg = _VG_ROOT not in sys.path
if _added_vg:
    sys.path.insert(0, _VG_ROOT)

from workers.worker_generate_video import (  # noqa: E402
    LAST_SCREENCAST_FRAME_TAIL_SEC,
    find_matching_screenshots,
)

if _added_vg:
    sys.path.remove(_VG_ROOT)


def test_clicker_find_matching_screenshots_matches_worker():
    """Логика в clicker (inline video) совпадает с video-generate-service."""
    assert CLICKER_TAIL == LAST_SCREENCAST_FRAME_TAIL_SEC
    log_data = [
        {"type": "before", "callId": "c1", "pageId": "p1", "startTime": 1000},
        {"type": "after", "callId": "c1", "endTime": 5000},
        {"type": "screencast-frame", "pageId": "p1", "timestamp": 5200, "sha1": "c"},
    ]
    assert find_matching_screenshots(log_data) == find_matching_screenshots_clicker(log_data)


def test_last_screencast_after_end_time_gets_tail_duration():
    """Если timestamp последнего кадра > after.endTime, duration должна быть положительной (хвост)."""
    log_data = [
        {"type": "before", "callId": "c1", "pageId": "p1", "startTime": 1000},
        {"type": "after", "callId": "c1", "endTime": 5000},
        {"type": "screencast-frame", "pageId": "p1", "timestamp": 2000, "sha1": "a"},
        {"type": "screencast-frame", "pageId": "p1", "timestamp": 4500, "sha1": "b"},
        # кадр после завершения call — раньше отбрасывался из-за duration < 0
        {"type": "screencast-frame", "pageId": "p1", "timestamp": 5200, "sha1": "c"},
    ]
    shots = find_matching_screenshots(log_data)
    assert len(shots) == 3
    last = shots[-1]
    assert last["sha1"] == "c"
    assert last["duration"] == LAST_SCREENCAST_FRAME_TAIL_SEC


def test_middle_frames_unchanged_delta():
    log_data = [
        {"type": "before", "callId": "c1", "pageId": "p1", "startTime": 1000},
        {"type": "after", "callId": "c1", "endTime": 9000},
        {"type": "screencast-frame", "pageId": "p1", "timestamp": 2000, "sha1": "a"},
        {"type": "screencast-frame", "pageId": "p1", "timestamp": 5000, "sha1": "b"},
    ]
    shots = find_matching_screenshots(log_data)
    assert len(shots) == 2
    assert abs(shots[0]["duration"] - 3.0) < 0.001
    d1 = (9000 - 5000) / 1000
    assert abs(shots[1]["duration"] - d1) < 0.001
