"""set products category_id as foreign key

Revision ID: cd9c239e42b4
Revises: 8e5024d6a191
Create Date: 2026-06-09 21:26:03.492795

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cd9c239e42b4'
down_revision: Union[str, None] = '8e5024d6a191'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with open(f"alembic/sql/{revision}/up.sql") as file:
        op.execute(file.read())


def downgrade() -> None:
    with open(f"alembic/sql/{revision}/down.sql") as file:
        op.execute(file.read())