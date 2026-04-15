"""Tests for MinIO bucket/file validation in vlm_step_dom_artifacts."""
from codegen.vlm_step_dom_artifacts import _minio_ref_path


def test_allowed_bucket_passes():
    ref = {"bucket": "run-cases", "file": "some/path.json"}
    result = _minio_ref_path(ref)
    assert result == ("run-cases", "some/path.json")


def test_screenshots_bucket_passes():
    ref = {"bucket": "screenshots", "file": "img.png"}
    result = _minio_ref_path(ref)
    assert result == ("screenshots", "img.png")


def test_disallowed_bucket_rejected():
    ref = {"bucket": "secret-bucket", "file": "data.json"}
    result = _minio_ref_path(ref)
    assert result is None


def test_path_traversal_rejected():
    ref = {"bucket": "run-cases", "file": "../../etc/passwd"}
    result = _minio_ref_path(ref)
    assert result is None


def test_path_traversal_middle_rejected():
    ref = {"bucket": "run-cases", "file": "legit/../../../etc/shadow"}
    result = _minio_ref_path(ref)
    assert result is None


def test_absolute_path_rejected():
    ref = {"bucket": "run-cases", "file": "/etc/passwd"}
    result = _minio_ref_path(ref)
    assert result is None


def test_none_ref_returns_none():
    assert _minio_ref_path(None) is None


def test_missing_file_returns_none():
    assert _minio_ref_path({"bucket": "run-cases"}) is None


def test_empty_file_returns_none():
    assert _minio_ref_path({"bucket": "run-cases", "file": ""}) is None


def test_whitespace_stripped():
    ref = {"bucket": " run-cases ", "file": " path.json "}
    result = _minio_ref_path(ref)
    assert result == ("run-cases", "path.json")
