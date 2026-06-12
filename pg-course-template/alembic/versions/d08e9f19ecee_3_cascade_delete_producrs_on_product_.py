"""[3]: cascade delete producrs on product_category delete

Revision ID: d08e9f19ecee
Revises: df27b54cbdad
Create Date: 2026-06-12 22:09:35.438165

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd08e9f19ecee'
down_revision: Union[str, None] = 'df27b54cbdad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with open(f"alembic/sql/{revision}/up.sql") as file:
        op.execute(file.read())


def downgrade() -> None:
    with open(f"alembic/sql/{revision}/down.sql") as file:
        op.execute(file.read())