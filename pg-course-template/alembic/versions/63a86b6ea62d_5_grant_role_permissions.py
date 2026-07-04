"""[5]: grant role permissions

Revision ID: 63a86b6ea62d
Revises: 0cec3b4e0cf0
Create Date: 2026-06-27 21:07:30.304607

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "63a86b6ea62d"
down_revision: Union[str, None] = "0cec3b4e0cf0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with open(f"alembic/sql/{revision}/up.sql") as file:
        op.execute(file.read())


def downgrade() -> None:
    with open(f"alembic/sql/{revision}/down.sql") as file:
        op.execute(file.read())
