"""merge heads

Revision ID: d49c5742c406
Revises: 4d9fc7479ad0, 3f4e72b91edf
Create Date: 2023-07-21 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd49c5742c406'
down_revision = None
branch_labels = None
depends_on = None

# We need to specify which revisions this one merges
revises = ('4d9fc7479ad0', '3f4e72b91edf')

def upgrade():
    # This is a migration that merges multiple heads.
    # It doesn't need to do anything since the migrations it's merging already handle their own upgrades
    pass


def downgrade():
    # Same as the upgrade, this doesn't need to do anything 
    pass
