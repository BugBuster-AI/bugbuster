"""Unit-тесты invalidate_codegen_artifact (мок AsyncSession, без БД)."""
from __future__ import annotations

from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, call
from uuid import uuid4

from api.services.codegen_eligibility import invalidate_codegen_artifact


class _FakeScalars:
    def __init__(self, first_val):
        self._first = first_val

    def first(self):
        return self._first


class _FakeResult:
    def __init__(self, first_val):
        self._first = first_val

    def scalars(self):
        return _FakeScalars(self._first)


class TestInvalidateCodegenArtifact(IsolatedAsyncioTestCase):
    async def test_deletes_artifact_and_clears_run_case(self):
        artifact = MagicMock()
        artifact.id = uuid4()

        case_id = uuid4()
        call_count = {"i": 0}

        async def exec_side(stmt, *_a, **_kw):
            call_count["i"] += 1
            if call_count["i"] == 1:
                return _FakeResult(artifact)
            return _FakeResult(None)

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=exec_side)

        result = await invalidate_codegen_artifact(session, case_id)

        self.assertTrue(result)
        self.assertEqual(session.execute.call_count, 3)

    async def test_returns_false_when_no_artifact(self):
        case_id = uuid4()

        async def exec_side(stmt, *_a, **_kw):
            return _FakeResult(None)

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=exec_side)

        result = await invalidate_codegen_artifact(session, case_id)

        self.assertFalse(result)
        self.assertEqual(session.execute.call_count, 1)


if __name__ == "__main__":
    import unittest

    unittest.main()
