"""release hardening migration

Revision ID: 20260419_0003
Revises: 20260419_0002
Create Date: 2026-04-19 10:05:00.000000
"""

from __future__ import annotations

# revision identifiers, used by Alembic.
revision = "20260419_0003"
down_revision = "20260419_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Reserved migration slot for release hardening."""


def downgrade() -> None:
    """Rollback release hardening slot."""

