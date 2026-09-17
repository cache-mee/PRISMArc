"""merge customers and staff branches

Revision ID: 83508f3f3cb4
Revises: 35506c641032, 8aac3e937d39
Create Date: 2026-09-17 20:10:29.232220

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '83508f3f3cb4'
down_revision: Union[str, Sequence[str], None] = ('35506c641032', '8aac3e937d39')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
