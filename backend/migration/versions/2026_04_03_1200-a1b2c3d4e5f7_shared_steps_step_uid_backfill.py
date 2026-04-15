"""Backfill step_uid for shared_steps.steps JSON

Revision ID: a1b2c3d4e5f7
Revises: f1a2b3c4d5e6
Create Date: 2026-04-03 12:00:00+00:00

"""
from __future__ import annotations

import json
import uuid as _uuid
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _assign_step_uids(steps: list) -> None:
    """Inline copy of assign_step_uids_new_shared_steps to keep migration self-contained."""
    seen: set[str] = set()
    for step in steps:
        if not isinstance(step, dict):
            continue
        if not step.get("step_uid"):
            step["step_uid"] = str(_uuid.uuid4())
        uid = str(step["step_uid"]).strip()
        if not uid or uid in seen:
            step["step_uid"] = str(_uuid.uuid4())
        seen.add(str(step["step_uid"]))


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(text("SELECT shared_steps_id, steps FROM shared_steps")).fetchall()
    for row in rows:
        sid = row[0]
        steps = row[1]
        if not isinstance(steps, list):
            continue
        _assign_step_uids(steps)
        bind.execute(
            text(
                "UPDATE shared_steps SET steps = CAST(:payload AS jsonb) "
                "WHERE shared_steps_id = CAST(:sid AS uuid)"
            ),
            {"payload": json.dumps(steps, ensure_ascii=False), "sid": str(sid)},
        )


def downgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(text("SELECT shared_steps_id, steps FROM shared_steps")).fetchall()
    for row in rows:
        sid = row[0]
        steps = row[1]
        if not isinstance(steps, list):
            continue
        changed = False
        for step in steps:
            if isinstance(step, dict) and "step_uid" in step:
                del step["step_uid"]
                changed = True
        if changed:
            bind.execute(
                text(
                    "UPDATE shared_steps SET steps = CAST(:payload AS jsonb) "
                    "WHERE shared_steps_id = CAST(:sid AS uuid)"
                ),
                {"payload": json.dumps(steps, ensure_ascii=False), "sid": str(sid)},
            )
