from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import exists, select
from sqlalchemy.engine import url
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.place import Place
from app.schemas.place import PlaceCreate, PlaceListCreateRequest
from app.service.naver_search_service import NaverSearchService
from app.service.place_service import PlaceService
from mapper.place_mapper import PlaceMapper


router = APIRouter(
    prefix="/places",
    tags=["places"],
)


# place_service =
def get_place_service():

    return PlaceService()


def get_naver_search_service():
    return NaverSearchService()


@router.get("/")
async def create_places(
    place_list: PlaceListCreateRequest,
    background_tasks: BackgroundTasks,
    place_service: PlaceService = Depends(get_place_service),
    db: Session = Depends(get_db),
):
    # 생성 후 background에서 리뷰 수집 및 임베딩하려고
    created_places = []

    for place_data in place_list.places:
        statement = select(exists().where(Place.title == place_data.title))
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
            db,
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

    urls: list[str] = naver_search_service._search_review_urls(
        create_place.title, create_place.address, 10
    )
    print(urls)

    return {
        "message": "success",
    }
