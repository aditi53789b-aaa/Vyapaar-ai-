
"""Quick local setup: create all tables directly (no migrations).

For the hackathon this is the fastest path. Alembic is configured if you
prefer proper migrations (see README). Run from the backend/ folder:

    python -m scripts.create_tables
"""
import app.models  # noqa: F401  (register models)
from app.database import Base, engine

Base.metadata.create_all(bind=engine)
print("All tables created in the database.")