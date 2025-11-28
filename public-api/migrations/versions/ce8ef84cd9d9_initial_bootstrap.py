"""Initial bootstrap

Revision ID: ce8ef84cd9d9
Revises: 
Create Date: 2025-11-24 09:40:16.735837

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ce8ef84cd9d9'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table("users",
                    sa.Column("user_name",sa.String(100),nullable= False))
    pass


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("users")
    pass
