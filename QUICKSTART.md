# 빠른 시작 가이드 (Quick Start)

이 문서는 장소 임베딩 시스템을 빠르게 시작하는 방법을 설명합니다.

## 📝 생성된 파일 목록

### 문서
- `place_embedding.md` - 전체 설계 문서 (ERD, 수식, 아키텍처)
- `IMPLEMENTATION_GUIDE.md` - 상세 구현 가이드
- `QUICKSTART.md` - 이 문서 (빠른 시작)

### 코드 파일
- `app/service/place_embedding_service.py` - 증분 임베딩 업데이트 서비스
- `app/service/recommendation_service.py` - 장소 추천 서비스
- `scripts/update_place_embeddings.py` - 임베딩 배치 업데이트 스크립트
- `scripts/check_embedding_consistency.py` - 데이터 정합성 체크 스크립트
- `alembic/versions/examples/add_place_embedding_fields.py` - 마이그레이션 예시

---

## 🚀 빠른 시작 (5단계)

### 1단계: 필수 패키지 설치

```bash
# pgvector 확장 설치 (PostgreSQL)
psql -d matetrip -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Python 패키지 설치
uv add numpy aiohttp
```

### 2단계: 데이터베이스 마이그레이션

```bash
# 마이그레이션 파일 생성
alembic revision -m "add_place_embedding_fields"

# 생성된 파일을 alembic/versions/examples/add_place_embedding_fields.py 내용으로 수정

# 마이그레이션 실행
alembic upgrade head

# 확인
psql -d matetrip -c "\d places"
```

### 3단계: 모델 파일 업데이트

#### app/models/place.py에 추가:

```python
from pgvector.sqlalchemy import Vector
from datetime import datetime

# 기존 필드 아래에 추가
embedding: Mapped[Optional[Vector]] = mapped_column(Vector(1024), nullable=True)
review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
embedding_sum: Mapped[Optional[Vector]] = mapped_column(Vector(1024), nullable=True)
last_embedding_update: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)
updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)
```

#### app/models/review.py에 추가:

```python
is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)
```

### 4단계: PlaceService 수정

`app/service/place_service.py`에서:

```python
from app.service.place_embedding_service import PlaceEmbeddingService

class PlaceService:
    def __init__(self) -> None:
        self.local_embedding_service = BedrockEmbeddingService()
        self.openai_service = OpenAIService()
        self.embedding_service = PlaceEmbeddingService()  # 🆕 추가

    async def process_place_reviews(self, db: Session, place: Place):
        # ... 기존 코드 ...

        # 6. 임베딩 생성 (기존 로직)
        texts = [str(review.content) for review in reviews]
        embeddings = self.local_embedding_service.create_embeddings_batch(texts)

        for review, embedding in zip(reviews, embeddings):
            review.embedding = embedding

        db.commit()

        # 🆕 7. 장소 임베딩 증분 업데이트 (새로 추가)
        self.embedding_service.update_place_embedding_incremental(
            db=db,
            place_id=place.id,
            new_review_embeddings=embeddings,
        )

        # ... 나머지 코드 ...
```

### 5단계: 배치 스크립트 실행

```bash
# 1. 기존 장소들의 임베딩 생성 (테스트)
python scripts/update_place_embeddings.py --limit 100

# 2. 리뷰 크롤링 (기존 스크립트)
python scripts/process_reviews_batch.py --batch 0 --total-batches 7

# 3. 정합성 체크
python scripts/check_embedding_consistency.py
```

---

## 📊 테스트 방법

### 임베딩 생성 확인

```sql
-- PostgreSQL에서 실행
SELECT
    title,
    review_count,
    last_embedding_update,
    embedding IS NOT NULL as has_embedding
FROM places
WHERE review_count > 0
ORDER BY last_embedding_update DESC
LIMIT 10;
```

### 추천 테스트

```python
# Python에서 테스트
from app.service.recommendation_service import RecommendationService
from app.database.database import SessionLocal

db = SessionLocal()
recommendation_service = RecommendationService()

# 더미 사용자 임베딩 (1024 차원)
import numpy as np
user_embedding = np.random.rand(1024).tolist()

# 추천 실행
places = recommendation_service.recommend_places_by_user_embedding(
    db=db,
    user_embedding=user_embedding,
    limit=10,
    min_review_count=3
)

for place in places:
    print(f"{place['title']} - 유사도: {place['similarity']:.3f}")
```

---

## 🔧 주요 명령어 모음

### 데이터 수집

```bash
# 장소 데이터 수집 (카카오 API)
python scripts/collect_places.py \
  --region 서울 \
  --category all \
  --api-key YOUR_KAKAO_KEY

# 리뷰 크롤링 (네이버 API)
python scripts/process_reviews_batch.py \
  --batch 0 \
  --total-batches 7 \
  --region 서울
```

### 임베딩 관리

```bash
# 임베딩이 없는 장소 처리
python scripts/update_place_embeddings.py --limit 1000

# 30일 이상 오래된 임베딩 갱신
python scripts/update_place_embeddings.py --limit 5000 --days 30

# 정합성 체크
python scripts/check_embedding_consistency.py

# 자동 수정
python scripts/check_embedding_consistency.py --auto-fix
```

### 데이터베이스 모니터링

```bash
# PostgreSQL 쿼리
psql -d matetrip

-- 임베딩 통계
SELECT
    COUNT(*) as total_places,
    COUNT(embedding) as with_embedding,
    AVG(review_count) as avg_reviews
FROM places;

-- 최근 업데이트
SELECT COUNT(*)
FROM places
WHERE last_embedding_update > NOW() - INTERVAL '7 days';
```

---

## 📖 더 자세한 내용

- **전체 설계**: `place_embedding.md` 참고
- **구현 가이드**: `IMPLEMENTATION_GUIDE.md` 참고
- **트러블슈팅**: `IMPLEMENTATION_GUIDE.md`의 섹션 7 참고

---

## ⚠️ 주의사항

1. **벡터 인덱스는 데이터 1,000개 이상 쌓인 후 생성**
   ```sql
   CREATE INDEX idx_places_embedding ON places
   USING ivfflat (embedding vector_cosine_ops)
   WITH (lists = 100);
   ```

2. **네이버 API 제한**: 하루 25,000건 (안전하게 20,000건으로 설정)

3. **AWS Bedrock 비용**: 월 $5 예상 (임베딩 생성)

4. **메모리 사용**: 대량 처리 시 배치 크기 조정 필요

---

## 🎯 다음 단계

1. ✅ 모델 파일 업데이트
2. ✅ PlaceService 수정
3. ✅ 마이그레이션 실행
4. ✅ 임베딩 배치 처리
5. ⬜ 벡터 인덱스 생성 (데이터 충분히 쌓인 후)
6. ⬜ 추천 API 엔드포인트 구현
7. ⬜ Cron 스케줄링 설정
8. ⬜ 모니터링 대시보드 구축

**작성일**: 2025-01-11
