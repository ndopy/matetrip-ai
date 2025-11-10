# 장소 임베딩 & 추천 설계 (경량화 버전)

최근 구조는 "간단함"을 최우선으로 합니다. 장소 테이블에는 `embedding` 하나만 남기고,
나머지 보조 컬럼(`embedding_sum`, `last_embedding_update`, `review_count` 등)은 모두 제거했습니다.
리뷰 수가 많지 않은 서비스라면 매번 평균을 다시 계산해도 충분히 빠르고, 무엇보다 데이터
정합성을 걱정할 부분이 크게 줄어듭니다.

## 1. 목표
- **장소 대표 임베딩**을 리뷰 임베딩의 단순 평균으로 유지
- **추가 파생 컬럼 없이** `places.embedding`만 관리
- 추천 쿼리는 **실시간 REVIEW COUNT**를 계산해 필터링
- 모든 상태 정보는 일반적인 `created_at` / `updated_at`으로 추적

---

## 2. 데이터 모델

### 2.1 places 테이블 (요약)
```sql
CREATE TABLE places (
    id UUID PRIMARY KEY,
    title TEXT NOT NULL,
    address TEXT NOT NULL,
    categories JSONB,
    tags JSONB,
    summary TEXT,
    image_url TEXT,
    longitude DOUBLE PRECISION NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    embedding VECTOR(1024),         -- 장소 대표 임베딩 (없을 수 있음)
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```
- `updated_at`은 SQLAlchemy onupdate + trigger 로 자동 갱신됩니다.
- 별도의 `embedding_sum`/`last_embedding_update` 컬럼이 없음에 주의.

### 2.2 place_review 테이블 (요약)
```sql
CREATE TABLE place_review (
    id UUID PRIMARY KEY,
    place_id UUID REFERENCES places(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    source_url TEXT NOT NULL UNIQUE,
    embedding VECTOR(1024),         -- 리뷰 임베딩 (없을 수 있음)
    is_deleted BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```
- `embedding`이 NULL이면 아직 임베딩을 만들지 않은 상태로 간주합니다.
- 모든 분석/추천 로직은 `is_deleted = FALSE AND embedding IS NOT NULL` 조건을 사용합니다.

---

## 3. PlaceEmbeddingService (평균 기반)

```python
class PlaceEmbeddingService:
    def __init__(self, minimum_reviews: int = 1):
        self.minimum_reviews = minimum_reviews

    def refresh_embedding(self, db: Session, place_id: UUID) -> list[float] | None:
        place = db.get(Place, place_id)
        if not place:
            raise ValueError("Place not found")

        vectors = db.execute(
            select(PlaceReview.embedding)
            .where(
                PlaceReview.place_id == place_id,
                PlaceReview.is_deleted == False,
                PlaceReview.embedding.isnot(None),
            )
        ).scalars()

        embeddings = [list(vec) for vec in vectors]
        if len(embeddings) < self.minimum_reviews:
            place.embedding = None
            db.commit()
            return None

        place.embedding = np.mean(np.array(embeddings, dtype=np.float32), axis=0).tolist()
        db.commit()
        return place.embedding
```
- 리뷰 추가/삭제/수정 후에는 **무조건 다시 평균**을 냅니다.
- 리뷰가 없으면 장소 임베딩을 비웁니다.
- 동일 서비스에서 사용 중인 `PlaceService.process_place_reviews`는 리뷰 임베딩 생성 후
  `refresh_embedding`만 호출하면 됩니다.

### 3.1 배치 업데이트
`scripts/update_place_embeddings.py`는 아래 전략을 따릅니다.
1. `embedding IS NULL` 이거나 `updated_at`이 오래된 장소를 검색
2. 각 장소에 대해서 리뷰 개수를 확인 (없으면 스킵)
3. `refresh_embedding`을 호출해 평균 벡터를 갱신

코드에서 `days` 파라미터를 0으로 주면 **임베딩이 없는 장소만** 처리합니다.

---

## 4. 추천 서비스 핵심 쿼리

### 4.1 리뷰 집계 뷰
모든 추천 쿼리는 동일한 CTE를 사용합니다.
```sql
WITH review_stats AS (
    SELECT place_id, COUNT(*) AS review_count
    FROM place_review
    WHERE is_deleted = FALSE
      AND embedding IS NOT NULL
    GROUP BY place_id
)
```
이렇게 만든 `review_stats`를 `places`와 `LEFT JOIN`하여 실시간 리뷰 수를 사용합니다.

### 4.2 사용자 임베딩 기반 추천
```sql
SELECT
    p.id, p.title, p.address,
    COALESCE(rs.review_count, 0) AS review_count,
    1 - (p.embedding <=> '[...]'::vector) AS similarity
FROM places p
LEFT JOIN review_stats rs ON rs.place_id = p.id
WHERE p.embedding IS NOT NULL
  AND COALESCE(rs.review_count, 0) >= :min_review_count
  AND p.address LIKE :region -- 옵션
  AND p.categories @> :category::jsonb -- 옵션
ORDER BY p.embedding <=> '[...]'::vector
LIMIT :limit;
```
- 사용자 임베딩은 pgvector literal (`[f1,f2,...]::vector`) 형태로 삽입합니다.
- 카테고리 필터는 `p.categories @> '["카페"]'::jsonb` 형태로 안전하게 바인딩합니다.

### 4.3 장소 유사도 & 위치 기반 추천
- 기준 장소 추천: `places p1 JOIN places p2` + 동일 `review_stats` join
- 위치 추천: 동일 CTE + 하버사인 거리 계산 + 유사도/거리 정렬

코드는 `app/service/recommendation_service.py`에 정리되어 있습니다.

---

## 5. 모니터링 / 유지보수

### 5.1 스크립트
- `scripts/check_embedding_consistency.py`
  - 임베딩은 있지만 리뷰가 없는 장소 탐지 → `refresh_embedding`으로 정리
  - 리뷰는 있는데 장소 임베딩이 비어 있는 케이스 출력
- `scripts/update_place_embeddings.py`
  - 배치 재계산 (cron 등에 연결)

### 5.2 자주 쓰는 쿼리
```sql
-- 리뷰는 있지만 임베딩이 없는 장소
SELECT p.id, p.title, COUNT(*) AS review_count
FROM places p
JOIN place_review pr ON pr.place_id = p.id
WHERE p.embedding IS NULL
  AND pr.is_deleted = FALSE AND pr.embedding IS NOT NULL
GROUP BY p.id, p.title
ORDER BY review_count DESC;

-- 임베딩이 있지만 리뷰가 없는 장소
WITH review_stats AS (
  SELECT place_id, COUNT(*) AS cnt
  FROM place_review
  WHERE is_deleted = FALSE AND embedding IS NOT NULL
  GROUP BY place_id
)
SELECT p.id, p.title
FROM places p
LEFT JOIN review_stats rs ON rs.place_id = p.id
WHERE p.embedding IS NOT NULL AND COALESCE(rs.cnt, 0) = 0;
```

### 5.3 운영 팁
- 리뷰 수가 적기 때문에 **증분 업데이트는 과도한 최적화**였습니다.
- 모든 변경 후 `updated_at`이 자동으로 바뀌므로, 스케줄러에서 `updated_at` 기준으로 오래된 장소를 재처리하면 됩니다.
- 벡터 인덱스(IVFFlat)는 데이터가 충분히 쌓인 뒤 `places.embedding`에만 생성하면 됩니다.

---

## 6. 마이그레이션 메모
- `migrations/002_simplify_place_embedding.sql`로 `embedding_sum`과 `last_embedding_update` 제거
- ORM 모델(`app/models/place.py`)도 동일하게 정리됨
- 추가 필드가 사라졌으므로 새로운 환경에서는 001 + 002 순서로 실행하면 최신 스키마를 얻습니다.

이 문서는 언제든지 실제 코드(`app/service/place_embedding_service.py`,
`app/service/recommendation_service.py`, `scripts/update_place_embeddings.py`)와 함께 확인하면 됩니다.
