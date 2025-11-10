# 장소 임베딩 시스템 구현 가이드

이 문서는 리뷰 기반 장소 임베딩 및 추천 시스템을 실제로 구현하고 실행하는 방법을 단계별로 설명합니다.

## 📋 목차

1. [사전 준비](#1-사전-준비)
2. [데이터베이스 마이그레이션](#2-데이터베이스-마이그레이션)
3. [코드 구현](#3-코드-구현)
4. [배치 스크립트 실행](#4-배치-스크립트-실행)
5. [스케줄링 설정](#5-스케줄링-설정)
6. [모니터링 및 유지보수](#6-모니터링-및-유지보수)
7. [트러블슈팅](#7-트러블슈팅)

---

## 1. 사전 준비

### 1.1 필요한 패키지 설치

```bash
# PostgreSQL에 pgvector 확장 설치 확인
# PostgreSQL에 접속하여:
CREATE EXTENSION IF NOT EXISTS vector;

# Python 패키지 설치
uv add numpy
uv add aiohttp  # 카카오 API용
```

### 1.2 환경 변수 확인

`.env` 파일에 다음 설정이 있는지 확인:

```bash
# AWS Bedrock
AWS_REGION=ap-northeast-2
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret

# 네이버 API
NAVER_CLIENT_ID=your_client_id
NAVER_CLIENT_SECRET=your_client_secret

# 카카오 API (장소 수집용)
KAKAO_REST_API_KEY=your_kakao_key

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/matetrip
```

---

## 2. 데이터베이스 마이그레이션

### 2.1 마이그레이션 파일 생성

```bash
# Alembic 마이그레이션 파일 생성
alembic revision -m "add_place_embedding_fields"
```

생성된 파일 (`alembic/versions/xxx_add_place_embedding_fields.py`)을 열어서 아래 내용으로 수정:

```python
"""add_place_embedding_fields

Revision ID: xxx
Revises: yyy
Create Date: 2025-01-11
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


def upgrade():
    # places 테이블에 임베딩 필드 추가
    op.add_column('places', sa.Column('embedding', Vector(1024), nullable=True))
    op.add_column('places', sa.Column('review_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('places', sa.Column('embedding_sum', Vector(1024), nullable=True))
    op.add_column('places', sa.Column('last_embedding_update', sa.TIMESTAMP(), nullable=True))
    op.add_column('places', sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False))

    # place_review 테이블에 필드 추가
    op.add_column('place_review', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('place_review', sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False))

    # source_url에 UNIQUE 제약 조건 추가 (중복 방지)
    op.create_unique_constraint('uq_place_review_source_url', 'place_review', ['source_url'])

    # 인덱스 생성
    # 주의: IVFFlat 인덱스는 데이터가 충분히 쌓인 후 생성하는 것을 권장
    # op.create_index('idx_places_embedding', 'places', ['embedding'],
    #                 postgresql_using='ivfflat',
    #                 postgresql_ops={'embedding': 'vector_cosine_ops'},
    #                 postgresql_with={'lists': 100})

    op.create_index('idx_places_review_count', 'places', ['review_count'])
    op.create_index('idx_place_review_is_deleted', 'place_review', ['is_deleted'])


def downgrade():
    op.drop_index('idx_place_review_is_deleted')
    op.drop_index('idx_places_review_count')
    # op.drop_index('idx_places_embedding')

    op.drop_constraint('uq_place_review_source_url', 'place_review')

    op.drop_column('place_review', 'updated_at')
    op.drop_column('place_review', 'is_deleted')

    op.drop_column('places', 'updated_at')
    op.drop_column('places', 'last_embedding_update')
    op.drop_column('places', 'embedding_sum')
    op.drop_column('places', 'review_count')
    op.drop_column('places', 'embedding')
```

### 2.2 마이그레이션 실행

```bash
# 마이그레이션 적용
alembic upgrade head

# 확인
psql -d matetrip -c "\d places"
psql -d matetrip -c "\d place_review"
```

### 2.3 벡터 인덱스 생성 (데이터 쌓인 후)

임베딩 데이터가 1,000개 이상 쌓인 후에 실행:

```sql
-- PostgreSQL에서 직접 실행
CREATE INDEX idx_places_embedding ON places
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 인덱스 생성 확인
\d places
```

---

## 3. 코드 구현

### 3.1 모델 파일 업데이트

#### app/models/place.py 수정

기존 파일에 필드 추가:

```python
# app/models/place.py

from typing import Optional, List
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy import JSON, TEXT, Float, String, Integer, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from pgvector.sqlalchemy import Vector
from app.models.base import Base


class Place(Base):
    __tablename__ = "places"

    # 기존 필드들...
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    title: Mapped[str] = mapped_column(TEXT, nullable=False)
    address: Mapped[str] = mapped_column(TEXT, nullable=False)
    categories: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(TEXT, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(TEXT, nullable=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)

    # 🆕 임베딩 관련 필드 추가
    embedding: Mapped[Optional[Vector]] = mapped_column(Vector(1024), nullable=True)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    embedding_sum: Mapped[Optional[Vector]] = mapped_column(Vector(1024), nullable=True)
    last_embedding_update: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationship
    reviews: Mapped[List["PlaceReview"]] = relationship("PlaceReview", back_populates="place")
```

#### app/models/review.py 수정

```python
# app/models/review.py

from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime
from pgvector.sqlalchemy import Vector
from sqlalchemy import TEXT, ForeignKey, TIMESTAMP, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


class PlaceReview(Base):
    __tablename__ = "place_review"

    # 기존 필드들...
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    place_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("places.id", ondelete="CASCADE"), nullable=False)
    content: Mapped[str] = mapped_column(TEXT, nullable=False)
    source_url: Mapped[str] = mapped_column(TEXT, nullable=False, unique=True)
    embedding: Mapped[Optional[Vector]] = mapped_column(Vector(1024), nullable=True)

    # 🆕 추가 필드
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationship
    place: Mapped["Place"] = relationship("Place", back_populates="reviews")
```

### 3.2 새 서비스 파일 생성

생성된 파일들은 다음 위치에 있습니다:
- `app/service/place_embedding_service.py`
- `app/service/recommendation_service.py`
- `scripts/update_place_embeddings.py`
- `scripts/collect_places.py`
- `scripts/check_embedding_consistency.py`

### 3.3 기존 PlaceService 수정

`app/service/place_service.py`에서 임베딩 자동 갱신 로직 추가:

```python
# app/service/place_service.py

from app.service.place_embedding_service import PlaceEmbeddingService

class PlaceService:
    def __init__(self) -> None:
        self.local_embedding_service = BedrockEmbeddingService()
        self.openai_service = OpenAIService()
        self.embedding_service = PlaceEmbeddingService()  # 🆕 추가

    async def process_place_reviews(self, db: Session, place: Place):
        """백그라운드에서 장소에 대한 리뷰를 처리하는 함수"""
        try:
            # ... 기존 로직 (1~6단계) ...

            # 6. 임베딩 생성
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

            # 8. 카테고리/태그/요약 생성 (기존 로직)
            # ...
```

---

## 4. 배치 스크립트 실행

### 4.1 전국 장소 데이터 수집

```bash
# 카카오 API 키 환경변수 설정
export KAKAO_REST_API_KEY="your_kakao_api_key"

# 서울 지역만 수집 (테스트)
python scripts/collect_places.py \
  --region 서울 \
  --category all \
  --api-key $KAKAO_REST_API_KEY

# 전국 모든 지역 수집
python scripts/collect_places.py \
  --region all \
  --category all \
  --api-key $KAKAO_REST_API_KEY

# 특정 카테고리만 수집 (예: 음식점)
python scripts/collect_places.py \
  --region all \
  --category FD6 \
  --api-key $KAKAO_REST_API_KEY
```

**예상 결과:**
```
================================================================================
전국 장소 데이터 수집 시작
대상 지역: 17개
대상 카테고리: 5개
================================================================================

[서울] 음식점 수집 중...
  수집: 675개, 저장: 650개

[서울] 카페 수집 중...
  수집: 450개, 저장: 430개

...

================================================================================
수집 완료!
- 총 수집: 85,000개
- 신규 저장: 80,000개
================================================================================
```

### 4.2 리뷰 크롤링 및 임베딩 생성

```bash
# 배치 0 실행 (전체의 0/7 ~ 1/7)
python scripts/process_reviews_batch.py \
  --batch 0 \
  --total-batches 7

# 특정 지역만 처리
python scripts/process_reviews_batch.py \
  --batch 0 \
  --total-batches 7 \
  --region 서울

# 네이버 API 호출 제한 조정
python scripts/process_reviews_batch.py \
  --batch 0 \
  --total-batches 7 \
  --max-naver-calls 15000
```

**예상 결과:**
```
================================================================================
리뷰 배치 처리 시작 (배치 0)
처리 대상: 1,000개 장소
네이버 API 제한: 20,000건
================================================================================

[1/1000] 경복궁 (서울특별시 종로구) 처리 중...
  ✓ 리뷰 처리 완료 (API 호출 누적: 5건)

[2/1000] 남산타워 (서울특별시 용산구) 처리 중...
  ✓ 리뷰 처리 완료 (API 호출 누적: 10건)

...

================================================================================
배치 0 처리 완료!
- 처리 완료: 950개
- 오류: 50개
- 네이버 API 호출 수: 4,750건
================================================================================
```

### 4.3 장소 임베딩 업데이트 (기존 데이터 처리)

```bash
# 임베딩이 없는 장소들 처리 (최대 1000개)
python scripts/update_place_embeddings.py --limit 1000

# 30일 이상 업데이트 안 된 장소들 처리
python scripts/update_place_embeddings.py --limit 5000 --days 30

# 전체 재계산 (주의: 시간 오래 걸림)
python scripts/update_place_embeddings.py --limit 100000 --days 0
```

**예상 결과:**
```
================================================================================
장소 임베딩 배치 업데이트 시작
대상 장소 수: 1000
================================================================================

[1/1000] 경복궁 처리 중...
[2/1000] 남산타워 처리 중...
...

================================================================================
배치 업데이트 완료!
- 성공: 980개
- 실패: 20개
================================================================================
```

### 4.4 데이터 정합성 체크

```bash
# 임베딩 데이터 정합성 확인
python scripts/check_embedding_consistency.py
```

---

## 5. 스케줄링 설정

### 5.1 Cron 스케줄 설정 (Linux/Mac)

```bash
# Crontab 편집
crontab -e
```

다음 내용 추가:

```bash
# 환경 변수 설정
KAKAO_REST_API_KEY=your_key
NAVER_CLIENT_ID=your_id
NAVER_CLIENT_SECRET=your_secret

# 매주 일요일 새벽 1시: 새로운 장소 데이터 수집
0 1 * * 0 cd /root/matetrip-ai && /usr/bin/python scripts/collect_places.py --region all --category all --api-key $KAKAO_REST_API_KEY >> /var/log/matetrip/collect.log 2>&1

# 매일 새벽 2시: 서울/경기 리뷰 크롤링 (배치 0)
0 2 * * * cd /root/matetrip-ai && /usr/bin/python scripts/process_reviews_batch.py --batch 0 --total-batches 7 --region 서울 >> /var/log/matetrip/batch0.log 2>&1

# 매일 새벽 3시: 부산/경남 리뷰 크롤링 (배치 1)
0 3 * * * cd /root/matetrip-ai && /usr/bin/python scripts/process_reviews_batch.py --batch 1 --total-batches 7 --region 부산 >> /var/log/matetrip/batch1.log 2>&1

# 매일 새벽 4시: 대구/경북 리뷰 크롤링 (배치 2)
0 4 * * * cd /root/matetrip-ai && /usr/bin/python scripts/process_reviews_batch.py --batch 2 --total-batches 7 --region 대구 >> /var/log/matetrip/batch2.log 2>&1

# 매일 새벽 5시: 광주/전라 리뷰 크롤링 (배치 3)
0 5 * * * cd /root/matetrip-ai && /usr/bin/python scripts/process_reviews_batch.py --batch 3 --total-batches 7 --region 광주 >> /var/log/matetrip/batch3.log 2>&1

# 매일 새벽 6시: 대전/충청 리뷰 크롤링 (배치 4)
0 6 * * * cd /root/matetrip-ai && /usr/bin/python scripts/process_reviews_batch.py --batch 4 --total-batches 7 --region 대전 >> /var/log/matetrip/batch4.log 2>&1

# 매일 새벽 7시: 강원/제주 리뷰 크롤링 (배치 5)
0 7 * * * cd /root/matetrip-ai && /usr/bin/python scripts/process_reviews_batch.py --batch 5 --total-batches 7 --region 강원 >> /var/log/matetrip/batch5.log 2>&1

# 매일 새벽 8시: 기타 지역 리뷰 크롤링 (배치 6)
0 8 * * * cd /root/matetrip-ai && /usr/bin/python scripts/process_reviews_batch.py --batch 6 --total-batches 7 >> /var/log/matetrip/batch6.log 2>&1

# 매일 오전 9시: 임베딩 업데이트
0 9 * * * cd /root/matetrip-ai && /usr/bin/python scripts/update_place_embeddings.py --limit 5000 >> /var/log/matetrip/embedding.log 2>&1

# 매주 월요일 오전 10시: 정합성 체크
0 10 * * 1 cd /root/matetrip-ai && /usr/bin/python scripts/check_embedding_consistency.py >> /var/log/matetrip/consistency.log 2>&1
```

### 5.2 로그 디렉토리 생성

```bash
# 로그 디렉토리 생성
sudo mkdir -p /var/log/matetrip
sudo chown $USER:$USER /var/log/matetrip

# 로그 파일 확인
tail -f /var/log/matetrip/batch0.log
```

### 5.3 Docker/AWS ECS 스케줄링 (선택사항)

**docker-compose.yml**

```yaml
version: '3.8'

services:
  review-crawler:
    build: .
    command: python scripts/process_reviews_batch.py --batch 0 --total-batches 7
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - NAVER_CLIENT_ID=${NAVER_CLIENT_ID}
      - NAVER_CLIENT_SECRET=${NAVER_CLIENT_SECRET}
    volumes:
      - ./logs:/var/log/matetrip

  embedding-updater:
    build: .
    command: python scripts/update_place_embeddings.py --limit 5000
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
```

---

## 6. 모니터링 및 유지보수

### 6.1 데이터베이스 모니터링

```bash
# PostgreSQL에 접속
psql -d matetrip

# 임베딩이 없는 장소 개수 확인
SELECT COUNT(*) FROM places WHERE embedding IS NULL;

# 리뷰는 있지만 임베딩이 없는 장소
SELECT p.id, p.title, COUNT(pr.id) as review_count
FROM places p
JOIN place_review pr ON p.id = pr.place_id
WHERE p.embedding IS NULL
GROUP BY p.id, p.title;

# 평균 리뷰 개수
SELECT AVG(review_count) FROM places WHERE review_count > 0;

# 최근 7일간 업데이트된 장소
SELECT COUNT(*) FROM places
WHERE last_embedding_update > NOW() - INTERVAL '7 days';

# 장소별 리뷰 개수 상위 10개
SELECT title, address, review_count
FROM places
ORDER BY review_count DESC
LIMIT 10;
```

### 6.2 성능 모니터링

```sql
-- 인덱스 사용률 확인
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename IN ('places', 'place_review')
ORDER BY idx_scan DESC;

-- 테이블 크기 확인
SELECT
    pg_size_pretty(pg_total_relation_size('places')) as places_size,
    pg_size_pretty(pg_total_relation_size('place_review')) as reviews_size;

-- 벡터 검색 성능 테스트
EXPLAIN ANALYZE
SELECT title, address, review_count
FROM places
WHERE embedding IS NOT NULL
ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 20;
```

### 6.3 로그 모니터링

```bash
# 최근 오류 로그 확인
grep "ERROR\|오류" /var/log/matetrip/*.log | tail -20

# 처리 완료된 장소 수 확인
grep "처리 완료" /var/log/matetrip/batch*.log | wc -l

# API 호출 수 확인
grep "API 호출" /var/log/matetrip/*.log | tail -10
```

---

## 7. 트러블슈팅

### 7.1 마이그레이션 실패

**문제:** `pgvector extension not found`

```bash
# 해결: PostgreSQL에 pgvector 설치
sudo apt-get install postgresql-15-pgvector

# PostgreSQL 재시작
sudo systemctl restart postgresql

# 확장 설치
psql -d matetrip -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 7.2 임베딩 생성 실패

**문제:** `AWS Bedrock connection timeout`

```python
# app/service/local_embedding_service.py에서 타임아웃 증가

self.bedrock_runtime = boto3.client(
    service_name="bedrock-runtime",
    region_name=bedrockConfig.AWS_REGION,
    aws_access_key_id=bedrockConfig.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=bedrockConfig.AWS_SECRET_ACCESS_KEY,
    config=boto3.session.Config(
        connect_timeout=60,
        read_timeout=60,
    )
)
```

### 7.3 메모리 부족

**문제:** `MemoryError during batch processing`

```python
# scripts/update_place_embeddings.py에서 배치 크기 줄이기

# 기존: --limit 10000
python scripts/update_place_embeddings.py --limit 500

# 또는 코드에서 직접 수정
BATCH_SIZE = 100  # 기본값에서 줄이기
```

### 7.4 벡터 인덱스 생성 실패

**문제:** `index row size exceeds btree maximum`

```sql
-- IVFFlat 인덱스 사용 (B-tree 대신)
CREATE INDEX idx_places_embedding ON places
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 데이터가 너무 적으면 lists 값 조정
-- 데이터 < 10,000개: lists = 10
-- 데이터 < 100,000개: lists = 100
-- 데이터 >= 100,000개: lists = sqrt(데이터 개수)
```

### 7.5 중복 데이터 처리

**문제:** `Duplicate key error on source_url`

```sql
-- 중복된 리뷰 찾기
SELECT source_url, COUNT(*)
FROM place_review
GROUP BY source_url
HAVING COUNT(*) > 1;

-- 중복 제거 (오래된 것 삭제)
DELETE FROM place_review a
USING place_review b
WHERE a.id < b.id
  AND a.source_url = b.source_url;
```

### 7.6 정합성 불일치

**문제:** `review_count와 실제 리뷰 개수 불일치`

```bash
# 정합성 체크 스크립트 실행
python scripts/check_embedding_consistency.py

# 문제 발견 시 전체 재계산
python scripts/update_place_embeddings.py --limit 100000 --days 0
```

---

## 8. 다음 단계

### 8.1 추천 API 사용

```python
# FastAPI 엔드포인트 예시
from app.service.recommendation_service import RecommendationService

@app.post("/api/recommendations")
async def get_recommendations(
    user_embedding: List[float],
    limit: int = 20,
    db: Session = Depends(get_db)
):
    recommendation_service = RecommendationService()
    places = recommendation_service.recommend_places_by_user_embedding(
        db=db,
        user_embedding=user_embedding,
        limit=limit,
        min_review_count=3
    )
    return places
```

### 8.2 성능 최적화

```sql
-- 벡터 검색 정확도 높이기
SET ivfflat.probes = 10;  -- 기본값: 1 (높을수록 정확하지만 느림)

-- 쿼리 성능 테스트
EXPLAIN ANALYZE SELECT * FROM places
WHERE embedding IS NOT NULL
ORDER BY embedding <=> '[...]'::vector
LIMIT 20;
```

### 8.3 확장 계획

1. **Phase 1 (1주):** 서울 전역 데이터 수집 → 20,000개
2. **Phase 2 (1개월):** 수도권 확장 → 50,000개
3. **Phase 3 (2개월):** 광역시 추가 → 80,000개
4. **Phase 4 (3개월):** 전국 완성 → 150,000개

---

## 📞 지원

문제가 발생하면:
1. 로그 파일 확인: `/var/log/matetrip/*.log`
2. 데이터베이스 상태 확인: 위 모니터링 쿼리 실행
3. GitHub Issues에 문제 등록

---

**작성일:** 2025-01-11
**버전:** 1.0.0
