"""Add PostGIS geography column to places

Revision ID: 003_add_postgis_geography
Revises: 002_add_tour_api_fields
Create Date: 2025-11-17 13:00:00

"""
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geography

# revision identifiers, used by Alembic.
revision = '003_add_postgis_geography'
down_revision = '002_add_tour_api_fields'
branch_labels = None
depends_on = None


def upgrade():
    # PostGIS geography 타입 컬럼 추가 (SRID 4326 = WGS84)
    op.execute(
        """
        ALTER TABLE places
        ADD COLUMN location GEOGRAPHY(POINT, 4326);
        """
    )

    # 기존 latitude, longitude 데이터로 geography 컬럼 채우기
    op.execute(
        """
        UPDATE places
        SET location = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL;
        """
    )

    # GiST 인덱스 생성 (공간 쿼리 성능 최적화)
    op.execute(
        """
        CREATE INDEX idx_places_location
        ON places USING GIST(location);
        """
    )


def downgrade():
    # 인덱스 삭제
    op.execute("DROP INDEX IF EXISTS idx_places_location;")

    # 컬럼 삭제
    op.execute("ALTER TABLE places DROP COLUMN IF EXISTS location;")
