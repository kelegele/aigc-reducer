"""migrate existing user IDs to random 10-digit numbers

Revision ID: c7a1f3e2d8b4
Revises: b48a6eafdfd2
Create Date: 2026-04-24 02:00:00.000000

"""
import random
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7a1f3e2d8b4'
down_revision: Union[str, Sequence[str], None] = 'b48a6eafdfd2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Migrate existing short user IDs to random 10-digit numbers."""
    conn = op.get_bind()

    # Disable FK checks for migration
    conn.execute(sa.text("SET CONSTRAINTS ALL DEFERRED"))
    # Drop FK constraints temporarily
    fk_names = [
        ("credit_accounts", "credit_accounts_user_id_fkey"),
        ("credit_transactions", "credit_transactions_user_id_fkey"),
        ("payment_orders", "payment_orders_user_id_fkey"),
    ]
    for table, fk in fk_names:
        conn.execute(sa.text(f"ALTER TABLE {table} DROP CONSTRAINT {fk}"))

    users = conn.execute(sa.text("SELECT id FROM users")).fetchall()
    used_ids = {row[0] for row in users}

    fk_tables = [
        ("credit_accounts", "user_id"),
        ("credit_transactions", "user_id"),
        ("payment_orders", "user_id"),
    ]

    for (old_id,) in users:
        if old_id >= 1000000000:
            continue  # already 10-digit

        # generate unique 10-digit id (int32 safe)
        new_id = random.randint(1000000000, 2147483647)
        while new_id in used_ids:
            new_id = random.randint(1000000000, 2147483647)
        used_ids.add(new_id)

        # update parent first, then children (PG FK constraint)
        conn.execute(sa.text("UPDATE users SET id = :new WHERE id = :old"),
                     {"new": new_id, "old": old_id})
        for table, col in fk_tables:
            conn.execute(sa.text(f"UPDATE {table} SET {col} = :new WHERE {col} = :old"),
                         {"new": new_id, "old": old_id})

    # Re-add FK constraints
    for table, fk in fk_names:
        conn.execute(sa.text(
            f"ALTER TABLE {table} ADD CONSTRAINT {fk} FOREIGN KEY (user_id) REFERENCES users(id)"
        ))


def downgrade() -> None:
    """Cannot reverse — original IDs are lost."""
    pass
