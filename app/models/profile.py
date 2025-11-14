from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.enums import Gender, MBTIType, TravelStyleType, TravelTendencyType


class Profile(BaseModel):
    id: UUID
    user_id: UUID
    profile_image_id: Optional[UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    nickname: str
    gender: Gender
    manner_temperature: Decimal = Field(default=Decimal("36.5"))
    intro: str
    description: str
    travel_styles: List[TravelStyleType] = Field(default_factory=list)
    tendency: List[TravelTendencyType] = Field(default_factory=list)
    mbti: MBTIType
    is_pass_auth: bool = False
    profile_embedding: Optional[list[float]] = None

    model_config = ConfigDict(from_attributes=True)
