"""task_id_uuid

Revision ID: 40cd6f7b0693
Revises: c6ba1a447bfb
Create Date: 2026-04-24 22:42:07.350375

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '40cd6f7b0693'
down_revision: Union[str, Sequence[str], None] = 'c6ba1a447bfb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. credit_transactions.ref_id: Integer -> String(36)
    op.alter_column('credit_transactions', 'ref_id',
               existing_type=sa.INTEGER(),
               type_=sa.String(length=36),
               existing_nullable=True)

    # 2. reduction_tasks.id: Integer -> String(36)
    # 先删除 reduction_paragraphs 的外键约束
    op.drop_constraint('reduction_paragraphs_task_id_fkey', 'reduction_paragraphs', type_='foreignkey')
    # 改 reduction_tasks.id 类型
    op.alter_column('reduction_tasks', 'id',
               existing_type=sa.INTEGER(),
               type_=sa.String(length=36),
               existing_nullable=False)
    # 改 reduction_paragraphs.task_id 类型
    op.alter_column('reduction_paragraphs', 'task_id',
               existing_type=sa.INTEGER(),
               type_=sa.String(length=36),
               existing_nullable=False)
    # 重建外键约束
    op.create_foreign_key('reduction_paragraphs_task_id_fkey', 'reduction_paragraphs', 'reduction_tasks', ['task_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    # 反向操作
    op.drop_constraint('reduction_paragraphs_task_id_fkey', 'reduction_paragraphs', type_='foreignkey')
    op.alter_column('reduction_paragraphs', 'task_id',
               existing_type=sa.String(length=36),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.alter_column('reduction_tasks', 'id',
               existing_type=sa.String(length=36),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.create_foreign_key('reduction_paragraphs_task_id_fkey', 'reduction_paragraphs', 'reduction_tasks', ['task_id'], ['id'], ondelete='CASCADE')
    op.alter_column('credit_transactions', 'ref_id',
               existing_type=sa.String(length=36),
               type_=sa.INTEGER(),
               existing_nullable=True)
