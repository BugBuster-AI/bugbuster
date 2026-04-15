"""get_playwright_codegen_status: source_run_id только при текущем артефакте."""
from __future__ import annotations

from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from api.codegen_actions import get_playwright_codegen_status


class TestGetPlaywrightCodegenStatus(IsolatedAsyncioTestCase):
    async def test_source_run_id_none_without_current_artifact(self):
        """После invalidate_codegen_artifact outerjoin даёт artifact=None — source_run_id null."""
        case_id = uuid4()
        user = MagicMock()
        user.active_workspace_id = uuid4()
        user.user_id = uuid4()

        case_row = MagicMock()
        case_row.codegen_regeneration_required = False
        case_row.codegen_regeneration_since = None
        case_row.codegen_first_requested_at = None

        fake_result = MagicMock()
        fake_result.first = MagicMock(return_value=(case_row, None))

        session = AsyncMock()
        session.execute = AsyncMock(return_value=fake_result)

        with patch("api.codegen_actions._get_codegen_job", return_value=None):
            out = await get_playwright_codegen_status(case_id, session, user, run_id=None)

        self.assertIsNone(out["source_run_id"])
        self.assertIn("job", out)

    async def test_source_run_id_returned_with_current_artifact(self):
        """When a current artifact exists, source_run_id should match artifact.source_run_id."""
        case_id = uuid4()
        source_run_id = uuid4()
        user = MagicMock()
        user.active_workspace_id = uuid4()
        user.user_id = uuid4()

        case_row = MagicMock()
        case_row.codegen_regeneration_required = False
        case_row.codegen_regeneration_since = None
        case_row.codegen_first_requested_at = None

        artifact = MagicMock()
        artifact.source_run_id = source_run_id

        fake_result = MagicMock()
        fake_result.first = MagicMock(return_value=(case_row, artifact))

        session = AsyncMock()
        session.execute = AsyncMock(return_value=fake_result)

        with patch("api.codegen_actions._get_codegen_job", return_value=None), patch(
            "api.codegen_actions.load_job_log", return_value=[]
        ):
            out = await get_playwright_codegen_status(case_id, session, user, run_id=None)

        self.assertEqual(out["source_run_id"], str(source_run_id))
        self.assertEqual(out["job"]["state"], "success")
        self.assertEqual(out["job"]["run_id"], str(source_run_id))
