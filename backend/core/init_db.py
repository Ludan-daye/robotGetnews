import os
from core.database import engine, Base, create_tables
from models import User, Preference, RepoCache, Recommendation, JobRun


def init_database():
    """Initialize database with all tables and indexes"""
    print("Creating database tables...")

    # Ensure database directory exists
    db_path = os.path.dirname(engine.url.database) if hasattr(engine.url, 'database') else None
    if db_path and not os.path.exists(db_path):
        os.makedirs(db_path, exist_ok=True)
        print(f"Created database directory: {db_path}")

    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

    # Print table information
    tables = Base.metadata.tables.keys()
    print(f"Created tables: {', '.join(tables)}")


if __name__ == "__main__":
    init_database()