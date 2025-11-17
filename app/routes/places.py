from typing import Optional, List
from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import exists, select
from sqlalchemy.engine import url
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.place import Place
from app.schemas.place import (
    PlaceCreate,
    PlaceListCreateRequest,
    NearbyPlaceResponse,
)
from app.service.crawling.naver_search_service import NaverSearchService
from app.service.place_service import PlaceService
from app.mapper.place_mapper import PlaceMapper


router = APIRouter(
    prefix="/places",
    tags=["places"],
)


def get_naver_search_service():
    return NaverSearchService()


@router.post("/")
async def create_places(
    place_list: PlaceListCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    # 생성 후 background에서 리뷰 수집 및 임베딩하려고
    created_places = []
    place_service = PlaceService(db)

    for place_data in place_list.places:
        statement = select(
            exists().where(
                (Place.title == place_data.title)
                & (Place.address == place_data.address)
            )
        )
        is_exists: bool | None = db.scalar(statement)

        if is_exists:
            created_places.append(place_data)
            continue

        place: Place = PlaceMapper.to_entity(place_data)

        db.add(place)  # 세션에 등록 -
        db.commit()
        db.refresh(place)  # 해당 객체를 DB에서 다시 읽어옴

        created_places.append(place)

        background_tasks.add_task(
            place_service.process_place_reviews,
            place,
        )

    return {
        "message": "success",
    }


@router.post("/naver-search")
async def naver_search_test(
    create_place: PlaceCreate,
    naver_search_service: NaverSearchService = Depends(get_naver_search_service),
):

    urls: list[str] = naver_search_service.search_review_urls(
        create_place.title, create_place.address
    )
    print(urls)

    return {
        "message": "success",
    }


@router.get("/nearby", response_model=List[NearbyPlaceResponse])
async def get_nearby_places(
    latitude: float = Query(..., description="위도"),
    longitude: float = Query(..., description="경도"),
    radius_km: float = Query(5.0, description="검색 반경 (km)"),
    category: Optional[str] = Query(
        None,
        description="카테고리 필터 (음식, 숙박, 레포츠, 자연, 인문(문화/예술/역사), 추천코스)",
    ),
    limit: int = Query(10, description="최대 결과 개수"),
    db: Session = Depends(get_db),
):
    """
    특정 좌표 주변의 장소를 검색합니다.

    - **latitude**: 기준 위도
    - **longitude**: 기준 경도
    - **radius_km**: 검색 반경 (km 단위)
    - **category**: 카테고리 필터 (선택사항)
    - **limit**: 최대 결과 개수
    """
    print("[get_nearby_places 함수 호출]")
    place_service = PlaceService(db)

    places = place_service.find_nearby_places(
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        category=category,
        limit=limit,
    )

    # Place 엔티티 -> DTO 변환
    return [
        NearbyPlaceResponse(
            id=str(place.id),
            title=place.title,
            address=place.address,
            category=place.category,
            tags=place.tags,
            summary=place.summary,
            image_url=place.image_url,
            latitude=place.latitude,
            longitude=place.longitude,
        )
        for place in places
    ]
