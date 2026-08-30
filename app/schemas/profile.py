from typing import List

from pydantic import BaseModel


class ProfileTextDto(BaseModel):
    """프로필 임베딩 입력 텍스트를 만드는 데 필요한 필드만 담은 DTO"""

    nickname: str
    intro: str
    description: str
    mbti: str
    travel_styles: List[str]
    tendency: List[str]

    def to_embedding_text(self) -> str:
        """프로필 소개 정보를 임베딩용 텍스트 하나로 합친다."""
        parts = [self.nickname, self.intro, self.description, self.mbti]
        parts.extend(self.travel_styles)
        parts.extend(self.tendency)
        return " ".join(p for p in parts if p)
