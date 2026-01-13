import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Load .env into process env vars
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Create a .env file (copy from .env.example) and set DATABASE_URL."
    )

# pool_pre_ping helps avoid stale connections
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    """
    FastAPI dependency that provides a SQLAlchemy session and always closes it.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
