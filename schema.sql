CREATE EXTENSION IF NOT EXISTS "vector";

CREATE EXTENSION IF NOT EXISTS pgcrypto;

DROP TABLE IF EXISTS place_review;

DROP TABLE IF EXISTS places;

CREATE TABLE
  places (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid (),
    title text NOT NULL,
    address text NOT NULL,
    category text NULL,
    tags jsonb NULL, -- Optional[list[str]] → jsonb (AI 생성 태그)
    summary text NULL, -- 리뷰 기반 AI 요약
    image_url text NULL, -- 장소 대표 이미지 URL
    longitude double precision NOT NULL,
    latitude double precision NOT NULL,
    embedding vector (1024) NULL, -- 장소 대표 임베딩 (리뷰 기반)
    created_at TIMESTAMP DEFAULT now () NOT NULL,
    updated_at TIMESTAMP DEFAULT now () NOT NULL
  );

-- 리뷰 테이블
CREATE TABLE
  place_review (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid (),
    place_id uuid NOT NULL REFERENCES places (id) ON DELETE CASCADE,
    content text NOT NULL,
    source_url text NOT NULL,
    embedding vector (1024) NULL, -- 리뷰 임베딩 (검색 정확도 향상용)
    is_deleted boolean DEFAULT false NOT NULL,
    created_at TIMESTAMP DEFAULT now () NOT NULL
  );