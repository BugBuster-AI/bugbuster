"""post_start_playwright_codegen: вызов invalidate_codegen_artifact при успешном старте; нет вызова при 409."""
from __future__ import annotations

from contextlib import asynccontextmanager
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException

from api.codegen_actions import post_start_playwright_codegen
from schemas import PlaywrightCodegenStartBody


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


@asynccontextmanager
async def _noop_transaction_scope(_session):
    yield


class TestPostStartInvalidateArtifact(IsolatedAsyncioTestCase):
    async def test_success_awaits_invalidate_codegen_artifact(self):
        case_id = uuid4()
        run_id = uuid4()
        body = PlaywrightCodegenStartBody(run_id=run_id, max_validation_attempts=3)
        user = MagicMock()
        user.active_workspace_id = uuid4()
        user.user_id = uuid4()

        case_row = MagicMock()
        case_row.codegen_first_requested_at = None

        session = AsyncMock()
        session.execute = AsyncMock(return_value=_FakeResult(case_row))

        inv = AsyncMock()

        with (
            patch("api.codegen_actions.codegen_job_running", return_value=False),
            patch(
                "api.codegen_actions.CodegenEligibilityService.can_start_codegen",
                new_callable=AsyncMock,
                return_value=(True, None),
            ),
            patch("api.codegen_actions.transaction_scope", _noop_transaction_scope),
            patch("api.codegen_actions.invalidate_codegen_artifact", inv),
            patch("api.codegen_actions._set_codegen_job"),
            patch("api.codegen_actions.init_empty_job_log"),
            patch("api.codegen_actions.send_to_rabbitmq", new_callable=AsyncMock),
        ):
            await post_start_playwright_codegen(case_id, body, session, user)

        inv.assert_awaited_once_with(session, case_id)

    async def test_success_publishes_to_rabbitmq_and_sets_redis_job(self):
        case_id = uuid4()
        run_id = uuid4()
        body = PlaywrightCodegenStartBody(run_id=run_id, max_validation_attempts=3)
        user = MagicMock()
        user.active_workspace_id = uuid4()
        user.user_id = uuid4()

        case_row = MagicMock()
        case_row.codegen_first_requested_at = None

        session = AsyncMock()
        session.execute = AsyncMock(return_value=_FakeResult(case_row))

        rabbit_mock = AsyncMock()
        redis_mock = MagicMock()

        with (
            patch("api.codegen_actions.codegen_job_running", return_value=False),
            patch(
                "api.codegen_actions.CodegenEligibilityService.can_start_codegen",
                new_callable=AsyncMock,
                return_value=(True, None),
            ),
            patch("api.codegen_actions.transaction_scope", _noop_transaction_scope),
            patch("api.codegen_actions.invalidate_codegen_artifact", new_callable=AsyncMock),
            patch("api.codegen_actions._set_codegen_job", redis_mock),
            patch("api.codegen_actions.init_empty_job_log"),
            patch("api.codegen_actions.send_to_rabbitmq", rabbit_mock),
            patch("api.codegen_actions.redis_client") as rc_mock,
        ):
            rc_mock.set.return_value = True
            result = await post_start_playwright_codegen(case_id, body, session, user)

        rabbit_mock.assert_awaited_once()
        redis_mock.assert_called_once()
        self.assertIn("task_id", result)

    async def test_codegen_in_progress_skips_invalidate(self):
        case_id = uuid4()
        run_id = uuid4()
        body = PlaywrightCodegenStartBody(run_id=run_id, max_validation_attempts=3)
        user = MagicMock()
        session = AsyncMock()

        inv = AsyncMock()

        with (
            patch("api.codegen_actions.codegen_job_running", return_value=True),
            patch("api.codegen_actions.invalidate_codegen_artifact", inv),
            patch("api.codegen_actions.redis_client") as rc_mock,
        ):
            rc_mock.set.return_value = True
            with self.assertRaises(HTTPException) as ctx:
                await post_start_playwright_codegen(case_id, body, session, user)

        self.assertEqual(ctx.exception.status_code, 409)
        inv.assert_not_called()
