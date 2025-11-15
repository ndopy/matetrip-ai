from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import exists, select
from sqlalchemy.engine import url
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.place import Place
from app.schemas.place import PlaceCreate, PlaceListCreateRequest
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
