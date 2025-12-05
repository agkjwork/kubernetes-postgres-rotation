"""Hello there

Revision ID: 62fc4e8a576c
Revises: ce8ef84cd9d9
Create Date: 2025-12-04 12:03:43.773963

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.

revision: str = '62fc4e8a576c'
down_revision: Union[str, Sequence[str], None] = 'ce8ef84cd9d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
