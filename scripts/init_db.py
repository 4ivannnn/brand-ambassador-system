"""Alternative to running database/schema.sql: create the tables straight from the SQLAlchemy models.

    python -m scripts.init_db

(schema.sql is the recommended route because it also creates the CHECK constraints,
trigger and reporting view. Use ONE of the two, not both.)
"""
from app.database import engine
from app.models import Base

if __name__ == "__main__":
    Base.metadata.create_all(engine)
    print("Tables created.")
