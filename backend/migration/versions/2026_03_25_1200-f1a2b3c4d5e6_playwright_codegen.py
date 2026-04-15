"""playwright codegen artifact and execution_engine

Revision ID: f1a2b3c4d5e6
Revises: ac93af5826b8
Create Date: 2026-03-25 12:00:00+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "ac93af5826b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "case_playwright_codegen",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("run_cases.run_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_code", sa.Text(), nullable=False),
        sa.Column("step_spans", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("steps_content_hash", sa.Text(), nullable=False),
        sa.Column("generator_meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.create_index("ix_case_playwright_codegen_case_id", "case_playwright_codegen", ["case_id"])
    op.execute(
        """
        CREATE UNIQUE INDEX uq_case_playwright_codegen_current
        ON case_playwright_codegen (case_id)
        WHERE is_current = true;
        """
    )
    op.add_column("cases", sa.Column("codegen_regeneration_required", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("cases", sa.Column("codegen_regeneration_since", sa.DateTime(timezone=True), nullable=True))
    op.add_column("cases", sa.Column("codegen_first_requested_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "run_cases",
        sa.Column("execution_engine", sa.String(length=32), server_default=sa.text("'vlm'"), nullable=False),
    )
    op.add_column("run_cases", sa.Column("playwright_codegen_artifact_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_run_cases_playwright_codegen_artifact",
        "run_cases",
        "case_playwright_codegen",
        ["playwright_codegen_artifact_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_run_cases_playwright_codegen_artifact", "run_cases", type_="foreignkey")
    op.drop_column("run_cases", "playwright_codegen_artifact_id")
    op.drop_column("run_cases", "execution_engine")
    op.drop_column("cases", "codegen_first_requested_at")
    op.drop_column("cases", "codegen_regeneration_since")
    op.drop_column("cases", "codegen_regeneration_required")
    op.execute("DROP INDEX IF EXISTS uq_case_playwright_codegen_current;")
    op.drop_index("ix_case_playwright_codegen_case_id", table_name="case_playwright_codegen")
    op.drop_table("case_playwright_codegen")
