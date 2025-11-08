from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from database.database import get_db
from models.place import Place
from schemas.place import PlaceListCreateRequest
from service.place_service import PlaceService, process_place_reviews


router = APIRouter(
    prefix="/places",
    tags=["places"],
)


# place_service =
def get_place_service():
    return PlaceService()


@router.get("/")
async def create_places(
    place_list: PlaceListCreateRequest,
    background_tasks: BackgroundTasks,
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

        place = Place(
            title=place_data.title,
            address=place_data.address,
            longitude=place_data.longitude,
            latitude=place_data.latitude,
        )

        db.add(place)  # 세션에 등록 -
        db.commit()
        db.refresh(place)  # 해당 객체를 DB에서 다시 읽어옴

        created_places.append(place)

        background_tasks.add_task(
            process_place_reviews,
            db,
            place,
        )

    return {
        "message": "success",
    }
