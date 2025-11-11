"""DB 마이그레이션 실행 스크립트"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database.database import engine

# 마이그레이션 SQL
migration_sql = """
-- Tour API 필드 추가
ALTER TABLE places ADD COLUMN IF NOT EXISTS tour_api_id VARCHAR(50);
ALTER TABLE places ADD COLUMN IF NOT EXISTS content_type_id VARCHAR(10);

-- data_source 컬럼 제거 (기존에 있었다면)
ALTER TABLE places DROP COLUMN IF EXISTS data_source;

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_places_tour_api_id ON places(tour_api_id);

-- 기존 data_source 인덱스 제거 (있었다면)
DROP INDEX IF EXISTS idx_places_data_source;
"""

def run_migration():
    """마이그레이션 실행"""
    with engine.connect() as conn:
        print("🔄 마이그레이션 시작...")

        # SQL 실행
        for statement in migration_sql.split(';'):
            statement = statement.strip()
            if statement:
                try:
                    conn.execute(text(statement))
                    print(f"✓ 실행: {statement[:50]}...")
                except Exception as e:
                    print(f"⚠ 오류 (무시 가능): {e}")

        conn.commit()
        print("✅ 마이그레이션 완료!")

if __name__ == "__main__":
    run_migration()
