-- 리뷰 임베딩 컬럼 추가 마이그레이션
-- 하이브리드 방식: 리뷰 임베딩 평균 → place.embedding

-- 1. review 테이블에 embedding 컬럼 추가
ALTER TABLE place_review
ADD COLUMN IF NOT EXISTS embedding vector(1024);

-- 2. 확인
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'place_review'
ORDER BY ordinal_position;
