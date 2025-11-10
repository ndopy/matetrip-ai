"""서울 25개 구의 중심 좌표 데이터"""

SEOUL_DISTRICTS = [
    # 테스트용 - 주요 5개 구만 활성화 (강남, 마포, 종로, 송파, 용산)
    {"name": "강남구", "longitude": 127.0495556, "latitude": 37.5145750},
    {"name": "마포구", "longitude": 126.9052778, "latitude": 37.5663889},
    {"name": "종로구", "longitude": 126.9816417, "latitude": 37.5730556},
    {"name": "송파구", "longitude": 127.1079306, "latitude": 37.5145556},
    {"name": "용산구", "longitude": 126.9816667, "latitude": 37.5311111},
    {"name": "강동구", "longitude": 127.1237708, "latitude": 37.52736667},
    {"name": "강북구", "longitude": 127.0277194, "latitude": 37.6395444},
    # {"name": "강서구", "longitude": 126.8495972, "latitude": 37.5509722},
    # {"name": "관악구", "longitude": 126.9515667, "latitude": 37.4781528},
    # {"name": "광진구", "longitude": 127.0845333, "latitude": 37.5384444},
    # {"name": "구로구", "longitude": 126.8895972, "latitude": 37.4954444},
    # {"name": "금천구", "longitude": 126.9001417, "latitude": 37.4519444},
    # {"name": "노원구", "longitude": 127.0583889, "latitude": 37.6542778},
    # {"name": "도봉구", "longitude": 127.0495222, "latitude": 37.6688889},
    # {"name": "동대문구", "longitude": 127.0421417, "latitude": 37.5742778},
    # {"name": "동작구", "longitude": 126.9395556, "latitude": 37.5124361},
    # {"name": "서대문구", "longitude": 126.9368472, "latitude": 37.5791111},
    # {"name": "서초구", "longitude": 127.0276194, "latitude": 37.4836111},
    # {"name": "성동구", "longitude": 127.0379306, "latitude": 37.5633611},
    # {"name": "성북구", "longitude": 127.0203333, "latitude": 37.5894444},
    # {"name": "양천구", "longitude": 126.8687083, "latitude": 37.5170028},
    # {"name": "영등포구", "longitude": 126.8983417, "latitude": 37.5263889},
    # {"name": "은평구", "longitude": 126.9312417, "latitude": 37.6176111},
    # {"name": "중구", "longitude": 126.9979417, "latitude": 37.5636111},
    # {"name": "중랑구", "longitude": 127.0947696, "latitude": 37.6063056},
]

# 카테고리 코드
CATEGORY_CODES = {
    "food": "FD6",  # 음식점
    "tourism": "AT4",  # 관광명소
    "cafe": "CE7",  # 카페
    "accommodation": "AD5",  # 숙박
    "culture": "CT1",  # 문화시설
}
