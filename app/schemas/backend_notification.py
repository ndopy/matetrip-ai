"""
Backend 알림용 DTO 스키마
AI Server → Backend Server 통신 시 사용
"""

from typing import List
from pydantic import BaseModel, Field


class PlaceReplacementItem(BaseModel):
    """단일 장소 교체 항목 DTO"""

    old_place_id: str = Field(..., description="교체할 기존 POI ID (UUID)")
    new_place_id: str = Field(..., description="새로 추가할 장소 ID")
    new_place_name: str = Field(..., description="새 장소명")
    latitude: float = Field(..., description="위도")
    longitude: float = Field(..., description="경도")
    address: str = Field(default="", description="주소")


class ReplaceScheduleNotification(BaseModel):
    """
    일정 내 장소 교체 알림 DTO (AI → Backend)
    """

    replacements: List[PlaceReplacementItem] = Field(
        ..., description="교체할 장소 목록 (1:1 매핑)"
    )
    source: str = Field(default="ai_replace", description="요청 출처 구분")

    @classmethod
    def create(
        cls,
        replaced_place_ids: List[str],
        new_places: List[dict],
        source: str = "ai_replace",
    ) -> "ReplaceScheduleNotification":
        """
        교체 알림 DTO 생성 팩토리 메서드

        Args:
            replaced_place_ids: 교체할 기존 POI ID 목록 (UUID)
            new_places: 새로 추천된 장소 목록 (NearbyPlaceResponse dict)
            source: 요청 출처

        Returns:
            ReplaceScheduleNotification DTO

        Raises:
            ValueError: 교체 대상과 새 장소 개수가 일치하지 않을 때
        """
        if len(replaced_place_ids) != len(new_places):
            raise ValueError(
                f"Replacement count mismatch: {len(replaced_place_ids)} old vs {len(new_places)} new"
            )

        replacements = [
            PlaceReplacementItem(
                old_place_id=old_id,
                new_place_id=str(new_place.get("id", "")),
                new_place_name=str(new_place.get("title", "")),
                latitude=float(new_place.get("latitude", 0.0)),
                longitude=float(new_place.get("longitude", 0.0)),
                address=str(new_place.get("address", "")),
            )
            for old_id, new_place in zip(replaced_place_ids, new_places)
        ]

        return cls(replacements=replacements, source=source)
