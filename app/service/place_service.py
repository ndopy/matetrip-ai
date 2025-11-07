from fastapi import BackgroundTasks
from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from models.place import Place
from schemas.place import PlaceListCreateRequest


class PlaceService:
    def __init__(self):
        pass


def process_place_revies(db: Session, place: Place):
    pass
