"""add_place_embedding_fields

이 파일은 마이그레이션 예시입니다.
실제 사용 시: alembic revision -m "add_place_embedding_fields" 명령어로 파일 생성 후
생성된 파일의 upgrade/downgrade 함수를 아래 내용으로 교체하세요.

Revision ID: xxx (자동 생성됨)
Revises: yyy (이전 마이그레이션 ID)
Create Date: 2025-01-11

"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


def upgrade():
    """
    places 및 place_review 테이블에 임베딩 관련 필드 추가
    """
    # ========================================
    # 1. places 테이블에 임베딩 필드 추가
    # ========================================

    # 장소 대표 임베딩 (리뷰들의 평균)
    op.add_column(
        "places", sa.Column("embedding", Vector(1024), nullable=True)
    )

    # 리뷰 임베딩의 합 (증분 업데이트 시 사용)
    # review_count는 제거 - DB 조회로 정합성 보장
    op.add_column(
        "places", sa.Column("embedding_sum", Vector(1024), nullable=True)
    )

    # 마지막 임베딩 업데이트 시각
    op.add_column(
        "places",
        sa.Column("last_embedding_update", sa.TIMESTAMP(), nullable=True),
    )

    # 수정 시각 (자동 업데이트)
    op.add_column(
        "places",
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ========================================
    # 2. place_review 테이블에 필드 추가
    # ========================================

    # 소프트 삭제 플래그
    op.add_column(
        "place_review",
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
    )

    # 수정 시각
    op.add_column(
        "place_review",
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ========================================
    # 3. 제약 조건 추가
    # ========================================

    # source_url에 UNIQUE 제약 조건 (중복 방지)
    # 주의: 기존에 중복 데이터가 있으면 실패할 수 있음
    try:
        op.create_unique_constraint(
            "uq_place_review_source_url", "place_review", ["source_url"]
        )
    except Exception as e:
        print(f"UNIQUE 제약 조건 추가 실패 (중복 데이터 확인 필요): {e}")

    # ========================================
    # 4. 인덱스 생성
    # ========================================

    # 소프트 삭제 인덱스 (리뷰 카운트 조회 시 사용)
    op.create_index("idx_place_review_is_deleted", "place_review", ["is_deleted"])

    # place_id와 is_deleted 복합 인덱스 (성능 향상)
    op.create_index(
        "idx_place_review_place_id_not_deleted",
        "place_review",
        ["place_id"],
        postgresql_where=sa.text("is_deleted = FALSE AND embedding IS NOT NULL")
    )

    # 마지막 업데이트 시각 인덱스
    op.create_index(
        "idx_places_last_embedding_update", "places", ["last_embedding_update"]
    )

    # ========================================
    # 5. 벡터 인덱스 생성 (선택사항)
    # ========================================

    # 주의: 벡터 인덱스는 데이터가 충분히 쌓인 후 (1,000개 이상) 생성 권장
    # 데이터가 적을 때 생성하면 성능 저하 가능

    # 아래 코드는 주석 처리해두고, 데이터 충분히 쌓인 후 직접 SQL로 실행하세요:
    """
    CREATE INDEX idx_places_embedding ON places
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
    """

    # 또는 Python 코드로:
    # op.create_index(
    #     "idx_places_embedding",
    #     "places",
    #     ["embedding"],
    #     postgresql_using="ivfflat",
    #     postgresql_ops={"embedding": "vector_cosine_ops"},
    #     postgresql_with={"lists": 100},
    # )

    print("✓ 마이그레이션 완료!")
    print("⚠ 벡터 인덱스는 데이터가 충분히 쌓인 후 수동으로 생성하세요.")


def downgrade():
    """
    마이그레이션 롤백
    """
    # 인덱스 삭제
    op.drop_index("idx_places_last_embedding_update", table_name="places")
    op.drop_index("idx_place_review_place_id_not_deleted", table_name="place_review")
    op.drop_index("idx_place_review_is_deleted", table_name="place_review")

    # 벡터 인덱스 삭제 (생성했을 경우)
    # op.drop_index("idx_places_embedding", table_name="places")

    # 제약 조건 삭제
    try:
        op.drop_constraint("uq_place_review_source_url", "place_review")
    except Exception:
        pass

    # place_review 컬럼 삭제
    op.drop_column("place_review", "updated_at")
    op.drop_column("place_review", "is_deleted")

    # places 컬럼 삭제
    op.drop_column("places", "updated_at")
    op.drop_column("places", "last_embedding_update")
    op.drop_column("places", "embedding_sum")
    op.drop_column("places", "embedding")

    print("✓ 롤백 완료!")
