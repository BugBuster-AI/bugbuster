"""Tests for codegen_limits: _i helper enforces non-negative values."""
import os
from unittest import mock

from codegen.codegen_limits import _i


def test_positive_value_passes():
    with mock.patch.dict(os.environ, {"TEST_LIMIT": "100"}):
        assert _i("TEST_LIMIT", 50) == 100


def test_negative_env_clamped_to_zero():
    with mock.patch.dict(os.environ, {"TEST_LIMIT": "-5"}):
        assert _i("TEST_LIMIT", 50) == 0


def test_invalid_env_returns_default():
    with mock.patch.dict(os.environ, {"TEST_LIMIT": "abc"}):
        assert _i("TEST_LIMIT", 42) == 42


def test_missing_env_returns_default():
    with mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop("TEST_LIMIT_MISSING", None)
        assert _i("TEST_LIMIT_MISSING", 99) == 99


def test_zero_value_passes():
    with mock.patch.dict(os.environ, {"TEST_LIMIT": "0"}):
        assert _i("TEST_LIMIT", 50) == 0
