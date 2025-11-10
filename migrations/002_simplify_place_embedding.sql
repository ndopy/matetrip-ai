-- ========================================
-- 장소 임베딩 필드 단순화
-- ========================================
--
-- 실행 방법:
--   docker exec sqlchemy-test psql -U postgres -d mateTrip -f /tmp/002_simplify_place_embedding.sql
--

-- 불필요한 필드 제거
ALTER TABLE places DROP COLUMN IF EXISTS embedding_sum;
ALTER TABLE places DROP COLUMN IF EXISTS last_embedding_update;

-- 인덱스 제거
DROP INDEX IF EXISTS idx_places_last_embedding_update;

-- 완료 메시지
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '✅ 단순화 완료!';
    RAISE NOTICE '';
    RAISE NOTICE '제거된 컬럼:';
    RAISE NOTICE '  - embedding_sum (불필요한 최적화)';
    RAISE NOTICE '  - last_embedding_update (updated_at으로 대체)';
    RAISE NOTICE '';
    RAISE NOTICE '남은 필드:';
    RAISE NOTICE '  - embedding (장소 대표 임베딩)';
    RAISE NOTICE '  - updated_at (마지막 수정 시각)';
    RAISE NOTICE '';
END $$;
