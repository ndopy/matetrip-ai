# 도구 이름과 프론트엔드 액션 매핑

TOOL_ACTION_MAP = {
    "create_travel_plan": [
        "UPDATE_MAP",       # 지도 업데이트
        "OPEN_SIDEBAR",     # 일정 목록 사이드바 열기
        "SHOW_TOAST"        # 성공 알림 띄우기
    ],

    "search_places": [
        "UPDATE_MAP",
        "SHOW_PLACE_LIST"
    ],

    # 인기 장소/주변 장소 추천도 지도와 목록을 갱신해야 프론트가 결과를 보여줄 수 있음
    "recommend_popular_places_in_region": [
        "UPDATE_MAP",
        "SHOW_PLACE_LIST"
    ],

    "recommend_nearby_places": [
        "UPDATE_MAP",
        "SHOW_PLACE_LIST"
    ],

    "recommend_next_poi": [
        "UPDATE_MAP",           # 추천 장소를 지도에 표시
        "SHOW_PLACE_LIST",      # 추천 장소 목록을 사이드바에 표시
        "SHOW_ANALYSIS_CARD"    # 일정 분석 결과 카드 표시 (부족한 카테고리 등)
    ]
}
