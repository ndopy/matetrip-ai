"""add_tour_api_fields_to_places

Tour API 통합을 위한 필드 추가:
- tour_api_id: Tour API의 contentId
- data_source: 데이터 출처 ('tour_api' | 'kakao_local')
- content_type_id: Tour API의 contenttypeid (12:관광지, 14:문화시설 등)

Revision ID: 002_add_tour_api_fields
Revises:
Create Date: 2025-01-11

"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    """
    places 테이블에 Tour API 관련 필드 추가
    """
    # Tour API의 contentId
    op.add_column(
        "places",
        sa.Column("tour_api_id", sa.String(50), nullable=True)
    )

    # 데이터 출처
    op.add_column(
        "places",
        sa.Column(
            "data_source",
            sa.String(20),
            nullable=False,
            server_default="kakao_local"
        )
    )

    # Tour API의 contenttypeid
    op.add_column(
        "places",
        sa.Column("content_type_id", sa.String(10), nullable=True)
    )

    # 인덱스 생성
    op.create_index("idx_places_tour_api_id", "places", ["tour_api_id"])
    op.create_index("idx_places_data_source", "places", ["data_source"])

    print("✓ Tour API 필드 추가 완료!")


def downgrade():
    """
    마이그레이션 롤백
    """
    # 인덱스 삭제
    op.drop_index("idx_places_data_source", table_name="places")
    op.drop_index("idx_places_tour_api_id", table_name="places")

    # 컬럼 삭제
    op.drop_column("places", "content_type_id")
    op.drop_column("places", "data_source")
    op.drop_column("places", "tour_api_id")

    print("✓ 롤백 완료!")
