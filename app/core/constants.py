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
    ]
}
