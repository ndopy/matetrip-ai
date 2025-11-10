from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PlaceRecommendation(BaseModel):
    """추천 응답 DTO."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Place identifier")
    title: str = Field(..., description="Place title")
    address: str = Field(..., description="Readable address")
    categories: Optional[list[str]] = Field(default=None, description="Categories")
    tags: Optional[list[str]] = Field(default=None, description="Tags")
    summary: Optional[str] = Field(default=None, description="Summary")
    image_url: Optional[str] = Field(default=None, description="Cover image URL")
    longitude: float = Field(..., description="Longitude")
    latitude: float = Field(..., description="Latitude")
    review_count: Optional[int] = Field(
        default=None, description="Number of associated reviews"
    )
    similarity: Optional[float] = Field(
        default=None, description="Cosine similarity score"
    )
    distance_km: Optional[float] = Field(
        default=None, description="Distance from query point (km)"
    )
    last_updated: Optional[datetime] = Field(
        default=None, description="Last updated timestamp"
    )

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> "PlaceRecommendation":
        payload = dict(getattr(row, "_mapping", row))
        return cls.model_validate(payload)

