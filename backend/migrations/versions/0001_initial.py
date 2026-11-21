"""Initial BoloKhaata schema.

This baseline is intended for a new production database. Future schema changes
must be added as forward-only Alembic revisions.
"""
from alembic import op
from app.main import Base

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    Base.metadata.create_all(bind=op.get_bind())

def downgrade():
    Base.metadata.drop_all(bind=op.get_bind())
