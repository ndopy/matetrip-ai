from fastapi import BackgroundTasks
from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from models.place import Place
from schemas.place import PlaceListCreateRequest


class PlaceService:
    def __init__(self):
        pass


"""
백그라운드에서 장소에 대한 리뷰를 처리하는 함수 
1. OpenAI로 리뷰 URL 추출
2. Crawl4AI로 리뷰 크롤링
3. 리뷰 저장 및 임베딩 생성
4. 태그 및 요약 생성 
"""


def process_place_reviews(db: Session, place: Place):

    print(f"process_place_reviews 시작 : {place.title}")

    pass
