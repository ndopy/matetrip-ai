-- ========================================
-- 장소 임베딩 시스템 마이그레이션
-- ========================================
--
-- 실행 방법:
--   docker exec sqlchemy-test psql -U postgres -d test_db -f /path/to/this/file.sql
--
-- 또는:
--   docker cp migrations/001_add_place_embedding_fields.sql sqlchemy-test:/tmp/
--   docker exec sqlchemy-test psql -U postgres -d test_db -f /tmp/001_add_place_embedding_fields.sql

-- pgvector 확장 생성 (이미 있으면 무시)
CREATE EXTENSION IF NOT EXISTS vector;

-- ========================================
-- 1. places 테이블에 임베딩 필드 추가
-- ========================================

-- 장소 대표 임베딩
ALTER TABLE places
ADD COLUMN IF NOT EXISTS embedding vector(1024);

-- 리뷰 임베딩의 합 (증분 업데이트용)
ALTER TABLE places
ADD COLUMN IF NOT EXISTS embedding_sum vector(1024);

-- 마지막 임베딩 업데이트 시각
ALTER TABLE places
ADD COLUMN IF NOT EXISTS last_embedding_update TIMESTAMP;

-- updated_at 컬럼
ALTER TABLE places
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- ========================================
-- 2. place_review 테이블에 필드 추가
-- ========================================

-- 소프트 삭제 플래그
ALTER TABLE place_review
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE NOT NULL;

-- updated_at 컬럼
ALTER TABLE place_review
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- source_url UNIQUE 제약조건 (중복 방지)
-- 주의: 중복 데이터가 있으면 실패할 수 있음
DO $$
BEGIN
    ALTER TABLE place_review
    ADD CONSTRAINT uq_place_review_source_url UNIQUE (source_url);
EXCEPTION
    WHEN duplicate_object THEN
        RAISE NOTICE 'Constraint uq_place_review_source_url already exists';
    WHEN unique_violation THEN
        RAISE NOTICE 'Duplicate source_url found - please clean up data first';
END $$;

-- ========================================
-- 3. 인덱스 생성
-- ========================================

-- 소프트 삭제 인덱스
CREATE INDEX IF NOT EXISTS idx_place_review_is_deleted
ON place_review(is_deleted);

-- place_id + is_deleted 복합 인덱스 (리뷰 카운트 조회 성능 향상)
CREATE INDEX IF NOT EXISTS idx_place_review_place_id_not_deleted
ON place_review(place_id)
WHERE is_deleted = FALSE AND embedding IS NOT NULL;

-- 마지막 업데이트 시각 인덱스
CREATE INDEX IF NOT EXISTS idx_places_last_embedding_update
ON places(last_embedding_update);

-- ========================================
-- 4. 트리거 생성 (updated_at 자동 업데이트)
-- ========================================

-- places 테이블 updated_at 트리거
CREATE OR REPLACE FUNCTION update_places_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_places_updated_at ON places;
CREATE TRIGGER trigger_update_places_updated_at
BEFORE UPDATE ON places
FOR EACH ROW
EXECUTE FUNCTION update_places_updated_at();

-- place_review 테이블 updated_at 트리거
CREATE OR REPLACE FUNCTION update_place_review_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_place_review_updated_at ON place_review;
CREATE TRIGGER trigger_update_place_review_updated_at
BEFORE UPDATE ON place_review
FOR EACH ROW
EXECUTE FUNCTION update_place_review_updated_at();

-- ========================================
-- 5. 벡터 인덱스 생성 (선택사항)
-- ========================================
--
-- ⚠️ 주의: 데이터가 1,000개 이상 쌓인 후 생성하세요!
--
-- CREATE INDEX idx_places_embedding ON places
-- USING ivfflat (embedding vector_cosine_ops)
-- WITH (lists = 100);

-- ========================================
-- 완료 메시지
-- ========================================

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '✅ 마이그레이션 완료!';
    RAISE NOTICE '';
    RAISE NOTICE '추가된 컬럼:';
    RAISE NOTICE '  places:';
    RAISE NOTICE '    - embedding (vector(1024))';
    RAISE NOTICE '    - embedding_sum (vector(1024))';
    RAISE NOTICE '    - last_embedding_update (timestamp)';
    RAISE NOTICE '    - updated_at (timestamp)';
    RAISE NOTICE '';
    RAISE NOTICE '  place_review:';
    RAISE NOTICE '    - is_deleted (boolean)';
    RAISE NOTICE '    - updated_at (timestamp)';
    RAISE NOTICE '';
    RAISE NOTICE '⚠️  벡터 인덱스는 데이터 1,000개 이상 쌓인 후 수동 생성하세요:';
    RAISE NOTICE '   CREATE INDEX idx_places_embedding ON places';
    RAISE NOTICE '   USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);';
    RAISE NOTICE '';
END $$;
