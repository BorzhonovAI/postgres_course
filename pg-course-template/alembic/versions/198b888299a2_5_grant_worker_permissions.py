"""5_grant_worker_permissions

Revision ID: 198b888299a2
Revises: a7f6ada2b95c
Create Date: 2026-06-27 18:10:11.149851

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '198b888299a2'
down_revision: Union[str, None] = 'a7f6ada2b95c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with open(f"alembic/sql/{revision}/up.sql") as file:
        op.execute(file.read())


def downgrade() -> None:
    with open(f"alembic/sql/{revision}/down.sql") as file:
        op.execute(file.read())