"""Add sido column to places table

Revision ID: 9c07292a78f4
Revises: 
Create Date: 2025-11-17 22:55:08.337533

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9c07292a78f4'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add sido column to places table."""
    # Add sido column with index
    op.add_column('places', sa.Column('sido', sa.TEXT(), nullable=True))
    op.create_index(op.f('ix_places_sido'), 'places', ['sido'], unique=False)


def downgrade() -> None:
    """Downgrade schema - Remove sido column from places table."""
    # Drop index and column
    op.drop_index(op.f('ix_places_sido'), table_name='places')
    op.drop_column('places', 'sido')
