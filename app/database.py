from sqlmodel import SQLModel, create_engine, Session
from contextlib import contextmanager
import os

AZURE_SQL_URL = os.getenv("AZURE_SQL_URL")

engine = create_engine(AZURE_SQL_URL, echo=False)

def init_db():
    SQLModel.metadata.create_all(engine)

@contextmanager
def get_session():
    with Session(engine) as session:
        yield session