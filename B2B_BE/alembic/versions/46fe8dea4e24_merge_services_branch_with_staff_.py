"""merge services branch with staff/customers/bookings branch

Revision ID: 46fe8dea4e24
Revises: 0001, c8354b5d4b5c
Create Date: 2026-09-17 20:24:23.446107

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '46fe8dea4e24'
down_revision: Union[str, Sequence[str], None] = ('0001', 'c8354b5d4b5c')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
