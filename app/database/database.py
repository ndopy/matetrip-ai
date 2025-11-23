from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.common.config import DatabaseConfig


dbConfig = DatabaseConfig()

engine = create_engine(dbConfig.sync_db_url())

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db():
    db = SessionLocal()  # 세션 인스턴스 생성
    try:
        yield db
    finally:
        db.close()  # 커넥션 정리 및 참조 끊음


# TODO: get_db를 아래로 다 바꾸기
@contextmanager
def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
