"""add_version_columns_and_account_index

Revision ID: 3c9f2d7e8a1b
Revises: b8693e5524d1
Create Date: 2026-10-31 16:55:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "3c9f2d7e8a1b"
down_revision = "b8693e5524d1"
branch_labels = None
depends_on = None


def upgrade():
    # Add version column to accounts
    op.add_column(
        "accounts",
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
    )
    # Add version column to transactions (optional, can be removed if not needed)
    op.add_column(
        "transactions",
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
    )
    # Create index on accounts.id (helps lock performance, though primary key already indexed)
    op.create_index("ix_accounts_id", "accounts", ["id"], unique=False)

    # Remove server defaults after column creation for cleaner schema
    op.alter_column("accounts", "version", server_default=None)
    op.alter_column("transactions", "version", server_default=None)


def downgrade():
    op.drop_index("ix_accounts_id", table_name="accounts")
    op.drop_column("transactions", "version")
    op.drop_column("accounts", "version")
