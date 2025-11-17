-- fix_null_regions.sql
-- region이 NULL인 데이터를 주소 기반으로 업데이트

-- 서울 (서울, 서울시, 서울특별시)
UPDATE places
SET region = '서울'
WHERE region IS NULL
  AND (address LIKE '서울%' OR address LIKE '서울시%' OR address LIKE '서울특별시%');

-- 부산
UPDATE places
SET region = '부산'
WHERE region IS NULL
  AND (address LIKE '부산%' OR address LIKE '부산광역시%');

-- 인천
UPDATE places
SET region = '인천'
WHERE region IS NULL
  AND (address LIKE '인천%' OR address LIKE '인천광역시%');

-- 대구
UPDATE places
SET region = '경상도'
WHERE region IS NULL
  AND (address LIKE '대구%' OR address LIKE '대구광역시%');

-- 울산
UPDATE places
SET region = '경상도'
WHERE region IS NULL
  AND (address LIKE '울산%' OR address LIKE '울산광역시%');

-- 경기도
UPDATE places
SET region = '경기도'
WHERE region IS NULL
  AND (address LIKE '경기%' OR address LIKE '경기도%');

-- 강원도
UPDATE places
SET region = '강원도'
WHERE region IS NULL
  AND (address LIKE '강원%' OR address LIKE '강원도%' OR address LIKE '강원특별자치도%');

-- 경상남도
UPDATE places
SET region = '경상도'
WHERE region IS NULL
  AND (address LIKE '경남%' OR address LIKE '경상남도%');

-- 경상북도
UPDATE places
SET region = '경상도'
WHERE region IS NULL
  AND (address LIKE '경북%' OR address LIKE '경상북도%');

-- 전라남도
UPDATE places
SET region = '전라도'
WHERE region IS NULL
  AND (address LIKE '전남%' OR address LIKE '전라남도%');

-- 전라북도
UPDATE places
SET region = '전라도'
WHERE region IS NULL
  AND (address LIKE '전북%' OR address LIKE '전라북도%' OR address LIKE '전북특별자치도%');

-- 충청남도
UPDATE places
SET region = '충청도'
WHERE region IS NULL
  AND (address LIKE '충남%' OR address LIKE '충청남도%');

-- 충청북도
UPDATE places
SET region = '충청도'
WHERE region IS NULL
  AND (address LIKE '충북%' OR address LIKE '충청북도%');

-- 대전
UPDATE places
SET region = '충청도'
WHERE region IS NULL
  AND (address LIKE '대전%' OR address LIKE '대전광역시%');

-- 세종
UPDATE places
SET region = '충청도'
WHERE region IS NULL
  AND (address LIKE '세종%' OR address LIKE '세종특별자치시%');

-- 광주
UPDATE places
SET region = '전라도'
WHERE region IS NULL
  AND (address LIKE '광주%' OR address LIKE '광주광역시%');

-- 제주도
UPDATE places
SET region = '제주도'
WHERE region IS NULL
  AND (address LIKE '제주%' OR address LIKE '제주도%' OR address LIKE '제주특별자치도%');

-- 결과 확인
SELECT
    COALESCE(region::text, 'NULL') as region,
    COUNT(*) as count
FROM places
GROUP BY region
ORDER BY count DESC;
