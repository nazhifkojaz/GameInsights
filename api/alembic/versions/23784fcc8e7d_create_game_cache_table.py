"""create game_cache table

Revision ID: 23784fcc8e7d
Revises:
Create Date: 2026-03-29 23:27:41.222004

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "23784fcc8e7d"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "game_cache",
        sa.Column("cache_key", sa.String(), nullable=False),
        sa.Column("endpoint", sa.String(), nullable=False),
        sa.Column("identifier", sa.String(), nullable=False),
        sa.Column("region", sa.String(), nullable=False),
        sa.Column("language", sa.String(), nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column(
            "cached_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ttl_seconds", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("cache_key"),
    )
    op.create_index("idx_game_cache_endpoint", "game_cache", ["endpoint"])


def downgrade() -> None:
    op.drop_index("idx_game_cache_endpoint", table_name="game_cache")
    op.drop_table("game_cache")
