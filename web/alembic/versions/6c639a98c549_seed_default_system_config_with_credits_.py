"""seed default system config with credits_per_1k_tokens=10

Revision ID: 6c639a98c549
Revises: c07d1924904f
Create Date: 2026-05-02 08:00:36.023320

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6c639a98c549'
down_revision: Union[str, Sequence[str], None] = 'c07d1924904f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "INSERT INTO system_config (key, value) VALUES ('credits_per_1k_tokens', '10.0') "
        "ON CONFLICT (key) DO NOTHING"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM system_config WHERE key = 'credits_per_1k_tokens' AND value = '10.0'"
    )
