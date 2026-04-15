"""Моки AsyncSession: can_start_codegen совпадает с контрактом POST/GET codegen_eligibility."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from api.services.codegen_eligibility import CodegenEligibilityService, CodegenEligibilityResult
from schemas import CaseFinalStatusEnum


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


def _session_double_execute(case, run):
    n = {"i": 0}

    async def exec_side_effect(*_a, **_kw):
        n["i"] += 1
        if n["i"] == 1:
            return _FakeResult(case)
        return _FakeResult(run)

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=exec_side_effect)
    return session


class TestCanStartCodegen(IsolatedAsyncioTestCase):
    async def test_allowed_passed_vlm_no_regeneration(self):
        case = MagicMock()
        case.codegen_regeneration_required = False
        case.codegen_regeneration_since = None

        run = MagicMock()
        run.status = CaseFinalStatusEnum.PASSED.value
        run.execution_engine = "vlm"
        run.end_dt = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)

        session = _session_double_execute(case, run)
        ok, reason = await CodegenEligibilityService.can_start_codegen(
            session,
            uuid4(),
            uuid4(),
            uuid4(),
            uuid4(),
        )
        self.assertTrue(ok)
        self.assertIsNone(reason)

    async def test_reject_run_not_passed(self):
        case = MagicMock()
        case.codegen_regeneration_required = False
        run = MagicMock()
        run.status = CaseFinalStatusEnum.FAILED.value
        run.execution_engine = "vlm"
        session = _session_double_execute(case, run)
        ok, reason = await CodegenEligibilityService.can_start_codegen(
            session, uuid4(), uuid4(), uuid4(), uuid4(),
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "run_not_passed")

    async def test_reject_run_not_vlm(self):
        case = MagicMock()
        case.codegen_regeneration_required = False
        run = MagicMock()
        run.status = CaseFinalStatusEnum.PASSED.value
        run.execution_engine = "playwright_js"
        session = _session_double_execute(case, run)
        ok, reason = await CodegenEligibilityService.can_start_codegen(
            session, uuid4(), uuid4(), uuid4(), uuid4(),
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "run_not_vlm")

    async def test_reject_stale_reference_after_nl_edit(self):
        case = MagicMock()
        case.codegen_regeneration_required = True
        case.codegen_regeneration_since = datetime(2026, 1, 10, 0, 0, tzinfo=timezone.utc)

        run = MagicMock()
        run.status = CaseFinalStatusEnum.PASSED.value
        run.execution_engine = "vlm"
        run.end_dt = datetime(2026, 1, 9, 0, 0, tzinfo=timezone.utc)

        session = _session_double_execute(case, run)
        ok, reason = await CodegenEligibilityService.can_start_codegen(
            session, uuid4(), uuid4(), uuid4(), uuid4(),
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "reference_run_stale_after_nl_edit")

    async def test_allowed_fresh_vlm_after_regeneration_since(self):
        case = MagicMock()
        case.codegen_regeneration_required = True
        case.codegen_regeneration_since = datetime(2026, 1, 10, 0, 0, tzinfo=timezone.utc)

        run = MagicMock()
        run.status = CaseFinalStatusEnum.PASSED.value
        run.execution_engine = "vlm"
        run.end_dt = datetime(2026, 1, 11, 0, 0, tzinfo=timezone.utc)

        session = _session_double_execute(case, run)
        ok, reason = await CodegenEligibilityService.can_start_codegen(
            session, uuid4(), uuid4(), uuid4(), uuid4(),
        )
        self.assertTrue(ok)
        self.assertIsNone(reason)

    async def test_reject_when_finished_at_naive_compare_utc(self):
        case = MagicMock()
        case.codegen_regeneration_required = True
        case.codegen_regeneration_since = datetime(2026, 1, 10, 0, 0, tzinfo=timezone.utc)

        run = MagicMock()
        run.status = CaseFinalStatusEnum.PASSED.value
        run.execution_engine = "vlm"
        run.end_dt = datetime(2026, 1, 9, 0, 0)

        session = _session_double_execute(case, run)
        ok, reason = await CodegenEligibilityService.can_start_codegen(
            session, uuid4(), uuid4(), uuid4(), uuid4(),
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "reference_run_stale_after_nl_edit")

    async def test_codegen_job_running_short_circuit(self):
        ok, reason = await CodegenEligibilityService.can_start_codegen(
            AsyncMock(),
            uuid4(),
            uuid4(),
            uuid4(),
            uuid4(),
            codegen_job_running=True,
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "codegen_in_progress")

    async def test_eligibility_result_wrapper(self):
        case = MagicMock()
        case.codegen_regeneration_required = False
        run = MagicMock()
        run.status = CaseFinalStatusEnum.PASSED.value
        run.execution_engine = "vlm"
        run.end_dt = datetime(2026, 1, 15, tzinfo=timezone.utc)
        session = _session_double_execute(case, run)
        res = await CodegenEligibilityService.eligibility_result(
            session, uuid4(), uuid4(), uuid4(), uuid4(),
        )
        self.assertIsInstance(res, CodegenEligibilityResult)
        self.assertTrue(res.allowed)
        self.assertIsNone(res.reason_code)


    async def test_reject_case_not_found(self):
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_FakeResult(None))
        ok, reason = await CodegenEligibilityService.can_start_codegen(
            session, uuid4(), uuid4(), uuid4(), uuid4(),
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "case_not_found")

    async def test_reject_run_not_found(self):
        case = MagicMock()
        case.codegen_regeneration_required = False

        session = _session_double_execute(case, None)
        ok, reason = await CodegenEligibilityService.can_start_codegen(
            session, uuid4(), uuid4(), uuid4(), uuid4(),
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "run_not_found")


if __name__ == "__main__":
    import unittest

    unittest.main()
