CREATE EXTENSION IF NOT EXISTS "pgvector";

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE
  places (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid (), -- 앱에서 uuid4() 쓰면 DEFAULT는 빼도 됨
    title text NOT NULL,
    address text NOT NULL,
    categories jsonb NULL, -- list[str] → jsonb
    tags jsonb NULL, -- Optional[list[str]] → jsonb
    summary text NULL,
    longitude double precision NOT NULL,
    latitude double precision NOT NULL
  );

-- 리뷰 테이블
CREATE TABLE
  place_review (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid (),
    place_id uuid NOT NULL REFERENCES places (id) ON DELETE CASCADE,
    content text NOT NULL,
    source_url text NOT NULL,
    embedding vector (768), -- pgvector 컬럼 (임베딩 768차원)
    created_at double precision -- 파이썬 float → double precision 매핑
  );