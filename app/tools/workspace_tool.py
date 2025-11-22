import httpx
from langchain_core.tools import tool

from app.common.config import nestJSConfig

BASE_URL = nestJSConfig.NESTJS_BACKEND_URL


def get_workspace_tools():
    """
    [워크스페이스 관련 도구 모음] - session_id를 workspace_id에 주입합니다.
    """
    @tool
    def recommend_places_by_all_users(workspace_id: str):
        """
        워크스페이스(게시글)에 참여 중인 모든 사용자의 성향을 종합해 모두가 좋아할 만한 장소를 추천합니다.
        사용자가 '우리 모두', '다같이 갈만한', '참여 인원 모두' 등의 표현으로 장소 추천을 요청할 때 사용하세요.

        Args:
            workspace_id (str): 추천의 기준이 될 워크스페이스의 고유 ID입니다.

        [답변 작성 규칙]
        1. 이 도구의 실행 결과에는 기술적인 정보(ID, 좌표 등)가 포함될 수 있습니다.
        2. 하지만 사용자에게 답변할 때는 **절대 기술적인 정보를 말하지 마세요.**
        3. 오직 **이름, 주소, 카테고리** 등 사람이 읽을 수 있는 정보만 사용하여 자연스럽게 요약해 주세요.
        """
        try:
            with httpx.Client() as client:
                # NestJS API 호출 (GET /workspace/{workspace_id}/recommendations)
                response = client.get(
                    f"{BASE_URL}/workspace/{workspace_id}/recommendations",
                )
                response.raise_for_status()
                data = response.json()
                return str(data) if data else "모두를 위한 추천 장소를 찾지 못했습니다."

        except Exception as e:
            return f"추천 장소 검색 중 에러 발생: {str(e)}"
        
    @tool
    def add_place_in_travel_itinerary(workspace_id: str, place_id: str, day_no: int):
        """
        사용자가 이전에 추천받거나 언급된 특정 장소를 여행 일정의 특정 날짜에 추가합니다.
        사용자가 '추가해줘', '저장해줘', '넣어줘' 등의 표현과 함께 '첫 번째 장소', '이 곳', '거기' 와 같이 대상을 명확히 하고, '첫째 날', '2일차' 처럼 날짜를 지정할 때 사용하세요.

        Args:
            workspace_id (str): 현재 사용자의 여행 계획에 해당하는 워크스페이스 ID입니다.
            place_id (str): 일정에 추가할 장소의 고유 ID입니다. 이 ID는 이전 대화나 도구 실행 결과에서 찾아야 합니다.
            day_no (int): 장소를 추가할 날짜 번호입니다. (예: 1은 1일차, 2는 2일차)

        [올바른 사용 예시]
        - User: "1번 장소 1일차에 넣어줘" -> add_place_in_travel_itinerary(workspace_id="...", place_id="...", day_no=1)
        - User: "아까 추천해준 두 번째 카페를 2일차 일정에 저장할래" -> add_place_in_travel_itinerary(workspace_id="...", place_id="...", day_no=2)

        [잘못된 사용 예시]
        - User: "강남역 추가해줘" -> X (어떤 장소인지 특정되지 않았고, 날짜 정보가 없음)
        - User: "1일차에 뭐하지?" -> X (장소를 추가하는 의도가 아님)
        """
        try:
            with httpx.Client() as client:
                # 1. day_no를 사용하여 planDayId를 조회합니다.
                plan_days_response = client.get(f"{BASE_URL}/workspace/{workspace_id}/plan-days")
                plan_days_response.raise_for_status()
                response_data = plan_days_response.json()
                # 백엔드 API가 JSON 배열을 직접 반환하므로, response_data를 그대로 사용합니다.
                plan_days_list = response_data
                
                print(plan_days_list)

                plan_day_id = None
                for day in plan_days_list:
                    if day.get("dayNo") == day_no:
                        plan_day_id = day.get("id")
                        break
                
                if not plan_day_id:
                    return f"{day_no}일차에 해당하는 일정을 찾을 수 없습니다."

                # 2. place_id를 사용하여 poiId를 조회합니다.
                # place_id를 기준으로 POI 정보를 직접 조회하는 API를 호출합니다.
                try:
                    poi_response = client.get(f"{BASE_URL}/workspace/{workspace_id}/poi/by-place/{place_id}")
                    poi_response.raise_for_status()  # 404 Not Found 시 예외 발생
                    poi_data = poi_response.json()
                    poi_id = poi_data.get("id")
                    
                    if not poi_id:
                        return f"장소(place_id: {place_id})에 해당하는 POI 정보를 찾았지만, ID가 없습니다."
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404:
                        return f"일정에 추가할 장소(place_id: {place_id})를 찾을 수 없습니다. 먼저 장소를 POI로 등록해야 할 수 있습니다."
                    # 다른 HTTP 오류는 그대로 전파
                    raise

                # 3. 조회한 ID들을 사용하여 최종 API를 호출합니다.
                response = client.post(
                    f"{BASE_URL}/workspace/poi/add-schedule", # NestJS의 'poi/add-schedule' 엔드포인트를 호출합니다.
                    json={
                        "workspaceId": workspace_id,
                        "planDayId": plan_day_id,
                        "poiId": poi_id,
                    },
                )
                response.raise_for_status()  # 2xx 상태 코드가 아니면 예외 발생
                # 성공 시, NestJS에서 반환하는 POI 정보를 그대로 반환하거나 성공 메시지를 반환할 수 있습니다.
                # 여기서는 간단히 성공 메시지를 반환합니다.
                return f"{day_no}일차 일정에 장소를 성공적으로 추가했습니다."
        except Exception as e:
            return f"장소 추가 중 에러 발생: {str(e)}"

    return [recommend_places_by_all_users, add_place_in_travel_itinerary]
