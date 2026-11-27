"""Add optional device location.

Revision ID: 20261127_0002
Revises: 20261127_0001
"""
from alembic import op
import sqlalchemy as sa


revision = "20261127_0002"
down_revision = "20261127_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("devices", sa.Column("location", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("devices", "location")