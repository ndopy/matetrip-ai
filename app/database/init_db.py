from re import A

from sqlalchemy import text
from app.database.database import engine
from models.base import Base


# DB 세팅 시 자동 테이블 및 pgvector 확장 설치
def init_database():

    with engine.connect() as conn:
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgvector"))
            conn.commit()

        except Exception as e:
            print(e)
            raise

    try:
        Base.metadata.create_all(bind=engine)

    except Exception as e:
        print(e)
        raise

    print("DB 세팅 완료")


if __name__ == "__main__":
    init_database()
