from pathlib import Path
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


def _db_path() -> Path:
    if getattr(sys, 'frozen', False):
        base = Path(sys.executable).resolve().parent
    else:
        base = Path(__file__).resolve().parents[1]
    data_dir = base / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / 'interencheres_public.db'

DATABASE_URL = f"sqlite:///{_db_path().as_posix()}"
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
