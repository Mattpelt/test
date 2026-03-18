import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_db():
    """Fournit une session base de données pour chaque requête API."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
