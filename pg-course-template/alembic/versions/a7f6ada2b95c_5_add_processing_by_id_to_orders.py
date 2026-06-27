"""[5]: add processing_by_id column to orders

Revision ID: a7f6ada2b95c
Revises: 9ac53cb77c24
Create Date: 2026-06-27 18:07:25.887138

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7f6ada2b95c'
down_revision: Union[str, None] = '9ac53cb77c24'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with open(f"alembic/sql/{revision}/up.sql") as file:
        op.execute(file.read())


def downgrade() -> None:
    with open(f"alembic/sql/{revision}/down.sql") as file:
        op.execute(file.read())