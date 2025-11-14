CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector; -- RDS에서만

DROP TABLE if exists poi_connection;
DROP TABLE IF EXISTS notification;
DROP TABLE if exists follow;
DROP TABLE IF EXISTS review;
DROP TABLE IF EXISTS post_participation;
DROP TABLE IF EXISTS poi;
DROP TABLE IF EXISTS plan_day;
DROP TABLE IF EXISTS chat_message;
DROP TABLE IF EXISTS workspace;
DROP TABLE IF EXISTS post;
DROP TABLE IF EXISTS profile;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS binary_content;
DROP TABLE IF EXISTS place_review;
DROP TABLE IF EXISTS places;

DROP TYPE IF EXISTS keyword_type;
DROP TYPE IF EXISTS gender;
DROP TYPE IF EXISTS post_status;
DROP TYPE IF EXISTS post_participation_status;
DROP TYPE IF EXISTS travel_tendency_type;
DROP TYPE IF EXISTS travel_style_type;
DROP TYPE IF EXISTS poi_status;
DROP TYPE if exists mbti_type;

CREATE TYPE region_group_type AS ENUM (
    '서울',
    '경기도',
    '인천',
    '강원',
    '부산',
    '경상',
    '전라도',
    '충청',
    '제주도'
);
CREATE TYPE keyword_type AS ENUM (
    '도심/야경 위주',
    '자연 위주',
    '바다/리조트 휴양',
    '로컬 동네/시골 감성',
    '맛집/먹방 중심',
    '카페/포토 스팟 탐방',
    '가벼운 야외활동',
    '강한 액티비티',
    '전시/유적/축제/공연 중심',
    '여유로운 일정',
    '빡빡한 일정',
    '가성비 중시',
    '편안한 휴양/힐링 중시',
    '소수/조용한 동행 선호',
    '활발/수다 많은 동행 선호'
    );
CREATE TYPE gender as ENUM ('남성', '여성');
CREATE TYPE post_status AS ENUM ('모집중','완료');
CREATE TYPE post_participation_status AS ENUM ('대기중', '승인', '거절');
CREATE TYPE travel_tendency_type AS ENUM (
    '도시',
    '시골',
    '전통도시',
    '휴양도시',
    '항구도시',
    '건축물탐방',
    '야경감상',
    '전통시장',
    '쇼핑',
    '바다',
    '섬',
    '산',
    '계곡',
    '호수',
    '꽃구경',
    '트레킹',
    '등산',
    '캠핑',
    '자전거',
    '서핑',
    '스노클링',
    '프리다이빙',
    '낚시',
    '스키',
    '스노보드',
    '골프',
    '박물관',
    '미술관',
    '유적지탐방',
    '공연뮤지컬',
    '콘서트',
    '스포츠관람',
    '놀이공원',
    '아쿠아리움',
    '동물원',
    '야시장',
    '현지축제',
    '길거리음식',
    '로컬레스토랑',
    '맛집탐방',
    '카페디저트',
    '호캉스',
    '경치드라이브',
    '조용한휴식',
    '렌터카',
    '오토바이여행',
    '캠핑카',
    '대중교통',
    '기차여행',
    '러닝',
    '빡빡한일정',
    '여유로운일정',
    '호텔',
    '리조트',
    '게스트하우스',
    '모텔',
    '펜션',
    '에어비앤비',
    '글램핑',
    '풀빌라',
    '비건필요',
    '돼지고기비선호',
    '해산물비선호',
    '매운맛선호',
    '순한맛선호',
    '해산물선호',
    '육류선호',
    '배낭여행',
    '운전가능',
    '사진촬영',
    '풍경촬영',
    '비흡연',
    '흡연',
    '비음주',
    '음주',
    '소수인원선호',
    '조용한동행선호',
    '수다떠는동행선호',
    '음식우선','숙소우선'
    );
CREATE TYPE travel_style_type AS ENUM ('모험적','즉흥적','계획적','느긋한','효율적','외향적','내향적','활동적','사교적','독립적','주도적','낭만','가성비','감성적','이성적','힐링');
CREATE TYPE poi_status AS ENUM ('MARKED', 'SCHEDULED');
CREATE TYPE mbti_type AS ENUM ('ISFJ', 'ISFP', 'ISTJ', 'ISTP', 'INFJ', 'INFP', 'INTJ', 'INTP', 'ESFJ', 'ESFP', 'ESTJ', 'ESTP', 'ENFJ', 'ENFP', 'ENTJ', 'ENTP');

CREATE TABLE IF NOT EXISTS binary_content
(
    id         UUID PRIMARY KEY     DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    file_name  TEXT        NOT NULL,
    file_type  TEXT        NOT NULL,
    file_size  BIGINT      NOT NULL
);

CREATE TABLE IF NOT EXISTS users
(
    id              UUID PRIMARY KEY     DEFAULT gen_random_uuid(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ,
    email           TEXT        NOT NULL,
    hashed_password TEXT        NOT NULL
);

CREATE TABLE IF NOT EXISTS profile
(
    id                 UUID PRIMARY KEY                DEFAULT gen_random_uuid(),
    user_id            UUID                   NOT NULL,
    profile_image_id   UUID,
    created_at         TIMESTAMPTZ            NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ,
    nickname           TEXT                   NOT NULL,
    gender             gender                 NOT NULL,
    manner_temperature NUMERIC(4, 1)          NOT NULL DEFAULT 36.5,
    intro              TEXT                   NOT NULL,
    description        TEXT                   NOT NULL,
    travel_styles      travel_style_type[]    NOT NULL DEFAULT '{}'::travel_style_type[],
    tendency           travel_tendency_type[] NOT NULL DEFAULT '{}'::travel_tendency_type[],
    mbti               mbti_type              NOT null,
    is_pass_auth       BOOLEAN                NOT NULL DEFAULT FALSE,
    profile_embedding  VECTOR(1024)
);

CREATE TABLE IF NOT EXISTS post
(
    id               UUID PRIMARY KEY     DEFAULT gen_random_uuid(),
    writer_id        UUID        NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    image_id  UUID,
    title            TEXT        NOT NULL,
    content          TEXT        NOT NULL,
    status           post_status NOT NULL DEFAULT '모집중',
    location         TEXT        NOT NULL,
    max_participants INT         NOT NULL DEFAULT 2,
    keywords         keyword_type[]       DEFAULT '{}'::keyword_type[],
    start_date       DATE        NULL,
    end_date         DATE        NULL
);

CREATE TABLE IF NOT EXISTS workspace
(
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id        UUID NOT NULL,
    workspace_name TEXT NOT NULL,
    memo           TEXT NULL
);

CREATE TABLE IF NOT EXISTS chat_message
(
    id           UUID PRIMARY KEY     DEFAULT gen_random_uuid(),
    user_id      UUID        NOT NULL,
    workspace_id UUID        NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ,
    content      TEXT        NOT NULL
);

CREATE TABLE IF NOT EXISTS plan_day
(
    id           UUID PRIMARY KEY     DEFAULT gen_random_uuid(),
    workspace_id UUID        NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    day_no       INT         NOT NULL,
    plan_date    DATE,
    CHECK (day_no >= 1)
);

CREATE TABLE IF NOT EXISTS poi
(
    id           UUID PRIMARY KEY          DEFAULT gen_random_uuid(),
    plan_day_id  UUID             NOT NULL,
    created_by   UUID             NOT NULL,
    created_at   TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
    place_name   TEXT             NOT NULL,
    longitude    DOUBLE PRECISION NOT NULL,
    latitude     DOUBLE PRECISION NOT NULL,
    address      TEXT             NOT NULL,
    status       poi_status       NOT NULL DEFAULT 'MARKED',
    sequence INT              NOT NULL DEFAULT 0,
    CHECK (longitude BETWEEN -180 AND 180),
    CHECK (latitude BETWEEN -90 AND 90)
);

-- CREATE TABLE IF NOT EXISTS poi_connection
-- (
--     id          UUID PRIMARY KEY     DEFAULT gen_random_uuid(),
--     prev_poi_id UUID,
--     next_poi_id UUID,
--     created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
--     plan_day_id UUID        NOT NULL,
--     distance    INT         NOT NULL DEFAULT 0,
--     duration    INT         NOT NULL DEFAULT 0,
--     CHECK (distance >= 0 AND duration >= 0),
--     CHECK (prev_poi_id IS NOT NULL OR next_poi_id IS NOT NULL) -- prev/next 둘 다 NULL 금지(최소 한쪽 연결)
-- );

CREATE TABLE IF NOT EXISTS post_participation
(
    id           UUID PRIMARY KEY                   DEFAULT gen_random_uuid(),
    requester_id UUID                      NOT NULL,
    post_id      UUID                      NOT NULL,
    requested_at TIMESTAMPTZ               NOT NULL DEFAULT NOW(),
    status       post_participation_status NOT NULL DEFAULT '대기중'
);

CREATE TABLE IF NOT EXISTS review
(
    id          UUID PRIMARY KEY       DEFAULT gen_random_uuid(),
    post_id     UUID,
    reviewer_id UUID          NOT NULL,
    reviewee_id UUID          NOT NULL,
    created_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    rating      NUMERIC(2, 1) NOT NULL,
    content     TEXT          NOT NULL,
    CHECK (rating >= 0 AND rating <= 5)
);

CREATE TABLE IF NOT EXISTS notification
(
    id         UUID PRIMARY KEY     DEFAULT gen_random_uuid(),
    user_id    UUID        NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    content    TEXT        NOT NULL,
    confirmed  BOOLEAN     NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS follow
(
    id           uuid PRIMARY KEY     DEFAULT gen_random_uuid(),
    follower_id  uuid        NOT NULL,
    following_id uuid        NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE TABLE places 
(
    id uuid PRIMARY KEY DEFAULT gen_random_uuid (),
    title text NOT NULL,
    address text NOT NULL,
    region_group region_group_type NOT NULL,
    category text NULL,
    tags jsonb NULL, -- Optional[list[str]] → jsonb (AI 생성 태그)
    summary text NULL, -- 리뷰 기반 AI 요약
    image_url text NULL, -- 장소 대표 이미지 URL
    longitude double precision NOT NULL,
    latitude double precision NOT NULL,
    embedding vector (1024) NULL, -- 장소 대표 임베딩 (리뷰 기반),
    created_at TIMESTAMP DEFAULT now () NOT NULL,
    updated_at TIMESTAMP DEFAULT now () NOT NULL
);

-- 리뷰 테이블
CREATE TABLE place_review 
(
    id uuid PRIMARY KEY DEFAULT gen_random_uuid (),
    place_id uuid NOT NULL REFERENCES places (id) ON DELETE CASCADE,
    content text NOT NULL,
    source_url text NOT NULL,
    embedding vector (1024) NULL, -- 리뷰 임베딩 (검색 정확도 향상용)
    is_deleted boolean DEFAULT false NOT NULL,
    created_at TIMESTAMP DEFAULT now () NOT NULL
);

-- ========= 2) ALTER TABLE: UNIQUE  =========
ALTER TABLE users
    ADD CONSTRAINT uq_users_email UNIQUE (email);
ALTER TABLE profile
    ADD CONSTRAINT uq_profile_user UNIQUE (user_id);
ALTER TABLE workspace
    ADD CONSTRAINT uq_workspace_post UNIQUE (post_id);
ALTER TABLE post_participation
    ADD CONSTRAINT uq_pp_unique UNIQUE (requester_id, post_id);
ALTER TABLE follow
    ADD CONSTRAINT uq_follow_unique UNIQUE (follower_id, following_id);

-- 3) ALTER TABLE: FOREIGN KEY
ALTER TABLE profile
    ADD CONSTRAINT fk_profile_user
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_profile_image
        FOREIGN KEY (profile_image_id) REFERENCES binary_content (id) ON DELETE SET NULL;

ALTER TABLE profile_embedding
    ADD CONSTRAINT  fk_profile_embedding_profile
        FOREIGN KEY (profile_id) REFERENCES profile (id) ON DELETE SET NULL;

ALTER TABLE post
    ADD CONSTRAINT fk_post_writer
        FOREIGN KEY (writer_id) REFERENCES users (id) ON DELETE RESTRICT;
    ADD CONSTRAINT fk_post_image
        FOREIGN KEY (image_id) REFERENCES binary_content (id) ON DELETE SET NULL;

ALTER TABLE workspace
    ADD CONSTRAINT fk_workspace_post
        FOREIGN KEY (post_id) REFERENCES post (id) ON DELETE CASCADE;

ALTER TABLE chat_message
    ADD CONSTRAINT fk_chatmsg_user
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_chatmsg_workspace
        FOREIGN KEY (workspace_id) REFERENCES workspace (id) ON DELETE CASCADE;

ALTER TABLE plan_day
    ADD CONSTRAINT fk_planday_workspace
        FOREIGN KEY (workspace_id) REFERENCES workspace (id) ON DELETE CASCADE;

ALTER TABLE poi
    ADD CONSTRAINT fk_poi_planday
        FOREIGN KEY (plan_day_id) REFERENCES plan_day (id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_poi_creator
        FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE restrict,
    ADD CONSTRAINT uq_poi_schedule UNIQUE (plan_day_id, sequence);


-- ALTER TABLE poi_connection
--     ADD CONSTRAINT fk_conn_prev FOREIGN KEY (prev_poi_id) REFERENCES poi (id) ON DELETE CASCADE,
--     ADD CONSTRAINT fk_conn_next FOREIGN KEY (next_poi_id) REFERENCES poi (id) ON DELETE CASCADE,
--     ADD CONSTRAINT fk_conn_planday FOREIGN KEY (plan_day_id) REFERENCES plan_day (id) ON DELETE CASCADE;
--     -- ADD CONSTRAINT fk_conn_creator FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE SET NULL;

ALTER TABLE post_participation
    ADD CONSTRAINT fk_pp_user FOREIGN KEY (requester_id) REFERENCES users (id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_pp_post FOREIGN KEY (post_id) REFERENCES post (id) ON DELETE CASCADE;

ALTER TABLE review
    ADD CONSTRAINT fk_review_post FOREIGN KEY (post_id) REFERENCES post (id) ON DELETE SET NULL,
    ADD CONSTRAINT fk_review_reviewer FOREIGN KEY (reviewer_id) REFERENCES users (id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_review_reviewee FOREIGN KEY (reviewee_id) REFERENCES users (id) ON DELETE RESTRICT;

ALTER TABLE Notification
    ADD CONSTRAINT fk_notification_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE;


ALTER TABLE follow
    ADD CONSTRAINT fk_follow_follower
        FOREIGN KEY (follower_id) REFERENCES users (id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_follow_following
        FOREIGN KEY (following_id) REFERENCES users (id) ON DELETE CASCADE,
    ADD CONSTRAINT chk_not_self CHECK ( follower_id <> following_id );


CREATE UNIQUE INDEX idx_unique_schedule
    on poi (plan_day_id, sequence)
    where sequence > 0;
-- ========= 인덱스 =========
-- CREATE INDEX idx_post_writer               ON post(writer_id);
-- CREATE INDEX idx_workspace_post_id         ON workspace(post_id);
-- CREATE INDEX idx_chat_message_workspace_ts ON chat_message(workspace_id, created_at);
-- CREATE INDEX idx_chat_message_user         ON chat_message(user_id);
-- CREATE INDEX idx_planday_workspace_day     ON plan_day(workspace_id, day_no);
-- CREATE INDEX idx_poi_planday               ON poi(plan_day_id);
-- CREATE INDEX idx_poi_creator               ON poi(created_by);
-- CREATE INDEX idx_poi_geo                   ON poi(longitude, latitude);
-- CREATE INDEX idx_conn_planday              ON poi_connection(plan_day_id);
-- CREATE INDEX idx_conn_prev                 ON poi_connection(prev_poi_id);
-- CREATE INDEX idx_conn_next                 ON poi_connection(next_poi_id);
-- CREATE INDEX idx_pp_post                   ON post_participation(post_id);
-- CREATE INDEX idx_pp_user                   ON post_participation(requester_id);
