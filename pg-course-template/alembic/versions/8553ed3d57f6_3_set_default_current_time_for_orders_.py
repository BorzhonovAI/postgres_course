"""[3]: set default current time for orders.created_at

Revision ID: 8553ed3d57f6
Revises: 804b7e3d7219
Create Date: 2026-06-12 18:51:22.360835

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8553ed3d57f6'
down_revision: Union[str, None] = '804b7e3d7219'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with open(f"alembic/sql/{revision}/up.sql") as file:
        op.execute(file.read())


def downgrade() -> None:
    with open(f"alembic/sql/{revision}/down.sql") as file:
        op.execute(file.read())