from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel

if TYPE_CHECKING:
    from app.models.review import PlaceReview


class ReviewCreateRequest(BaseModel):
    place_id: str
    content: str
    source_url: str


class ReviewCreateResponse(BaseModel):
    content: str


class ReviewContentDto(BaseModel):
    """크롤링/필터링 과정에서 사용하는 리뷰 DTO"""

    source_url: str
    content: str


class SavedReviewDto(BaseModel):
    """DB에 저장된 리뷰를 표현하는 DTO"""

    id: UUID
    place_id: UUID
    content: str
    source_url: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, review: "PlaceReview") -> "SavedReviewDto":
        return cls(
            id=review.id,
            place_id=review.place_id,
            content=review.content,
            source_url=review.source_url,
        )
