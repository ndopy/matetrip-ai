from sqlalchemy import text

from app.database.database import engine
from app.models.base import Base


# DB 세팅 시 자동 테이블 및 pgvector 확장 설치
# python -m app.database.init_db
def init_database():

    with engine.connect() as conn:
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()

        except Exception as e:
            print(e)
            raise

    try:
        print("DB 세팅 시작")
        Base.metadata.create_all(bind=engine)

    except Exception as e:
        print(e)
        raise

    print("DB 세팅 완료")


if __name__ == "__main__":
    init_database()
