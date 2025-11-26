"""Place 객체 정규화 유틸리티."""

from typing import Iterable, List

from app.schemas.place import SimplePlace


def to_simple_places(
    places_data: Iterable[SimplePlace | dict],
) -> List[SimplePlace]:
    """dict/Model 혼합 입력을 SimplePlace 리스트로 정규화."""
    normalized: List[SimplePlace] = []
    for place in places_data or []:
        if isinstance(place, SimplePlace):
            normalized.append(place)
            continue

        if isinstance(place, dict):
            try:
                normalized.append(SimplePlace.model_validate(place))
            except Exception:
                if "id" in place and "title" in place:
                    normalized.append(SimplePlace(id=place["id"], title=place["title"]))
    return normalized
