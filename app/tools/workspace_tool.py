import httpx
from typing import List

from langchain_core.tools import tool

from app.common.config import nestJSConfig

BASE_URL = nestJSConfig.NESTJS_BACKEND_URL


def get_workspace_tools():
    """
    [워크스페이스 관련 도구 모음] - session_id를 workspace_id에 주입합니다.
    """

    @tool
    def find_place_id_by_name(place_name: str) -> str:
        """
        장소 이름을 사용하여 데이터베이스에서 해당 장소의 고유 ID(place_id)를 찾습니다.
        사용자가 장소 이름을 언급하며 리뷰 조회 등 추가 정보를 요청할 때, 다른 도구(get_place_reviews)를 사용하기 위해 필요한 place_id를 얻기 위한 중간 단계로 사용하세요.

        Args:
            place_name (str): ID를 찾고자 하는 장소의 이름입니다.

        Returns:
            가장 유사도가 높은 장소의 place_id(문자열) 또는 장소를 찾지 못한 경우 에러 메시지를 반환합니다.
        """
        try:
            print(f"Requesting BASE_URL: {BASE_URL}")
            with httpx.Client() as client:                
                response = client.get(
                    f"{BASE_URL}/places/search", params={"name": place_name}
                )

                # 전체 URL을 로그로 출력합니다.
                print(f"Requesting full URL: {response.request.url}")

                response.raise_for_status()
                places = response.json()

                if not places:
                    return f"'{place_name}'에 해당하는 장소를 찾을 수 없습니다."
                return places["placeIds"][0]  # 가장 유사한 첫 번째 결과의 ID를 반환
        except Exception as e:
            return f"장소 ID 조회 중 에러 발생: {str(e)}"

    @tool
    def get_place_reviews(place_id: str) -> List[str] | str:
        """
        장소의 고유 ID를 사용하여 해당 장소의 최신 리뷰 10개를 가져옵니다.
        사용자가 특정 장소에 대한 리뷰나 사람들의 반응, 후기 등이 궁금하다고 할 때 사용하세요.

        Args:
            place_id (str): 리뷰를 조회할 장소의 고유 ID입니다.

        [답변 작성 규칙]
        1. 이 도구의 실행 결과는 리뷰 텍스트 목록입니다.
        2. 사용자에게 답변할 때는 이 리뷰들을 자연스럽게 요약해서 전달해야 합니다.
        3. "리뷰를 요약해드릴게요" 와 같은 직접적인 언급보다는, "이 장소에 대해서는 대체로 ~한 반응들이 많네요." 와 같이 자연스러운 어투를 사용하세요.
        """
        try:
            print(f"Requesting BASE_URL: {BASE_URL}")
            with httpx.Client() as client:
                # NestJS API 호출 (GET /place/{place_id})
                response = client.get(
                    f"{BASE_URL}/place-user-reviews/place/{place_id}",
                )
                response.raise_for_status()
                reviews = response.json().get("data", [])

                if not reviews:
                    return "해당 장소에 대한 리뷰를 찾을 수 없습니다."

                # 리뷰 내용만 추출하여 리스트로 반환
                return [review.get("content", "") for review in reviews]
        except Exception as e:
            return f"리뷰 조회 중 에러 발생: {str(e)}"

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
            print(f"Requesting BASE_URL: {BASE_URL}")
            with httpx.Client() as client:
                # NestJS API 호출 (GET /workspace/{workspace_id}/recommendations)
                response = client.get(
                    f"{BASE_URL}/workspace/{workspace_id}/recommendations",
                )
                response.raise_for_status()
                data = response.json()
                return data if data else "모두를 위한 추천 장소를 찾지 못했습니다."

        except Exception as e:
            return f"추천 장소 검색 중 에러 발생: {str(e)}"

    @tool
    def add_schedule_by_place(workspace_id: str, place_id: str, day_no: int) -> str:
        """
        사용자가 이전에 추천받거나 언급된 특정 장소를 여행 일정의 특정 날짜에 추가합니다.
        사용자가 '추가해줘', '저장해줘', '넣어줘' 등의 표현과 함께 '첫 번째 장소', '이 곳', '거기' 와 같이 대상을 명확히 하고, '첫째 날', '2일차' 처럼 날짜를 지정할 때 사용하세요.

        Args:
            workspace_id (str): 현재 사용자의 여행 계획에 해당하는 워크스페이스 ID입니다.
            place_id (str): 일정에 추가할 장소의 고유 ID입니다. 이 ID는 이전 대화나 도구 실행 결과에서 찾아야 합니다.
            day_no (int): 장소를 추가할 날짜 번호입니다. (예: 1은 1일차, 2는 2일차)

        [올바른 사용 예시]
        - User: "1번 장소 1일차에 넣어줘" -> add_schedule_by_place(workspace_id="...", place_id="...", day_no=1)
        - User: "아까 추천해준 두 번째 카페를 2일차 일정에 저장할래" -> add_schedule_by_place(workspace_id="...", place_id="...", day_no=2)

        [잘못된 사용 예시]
        - User: "강남역 추가해줘" -> X (어떤 장소인지 특정되지 않았고, 날짜 정보가 없음)
        - User: "1일차에 뭐하지?" -> X (장소를 추가하는 의도가 아님)
        """
        try:
            print(f"Requesting BASE_URL: {BASE_URL}")
            with httpx.Client() as client:
                response = client.post(
                    f"{BASE_URL}/workspace/schedule/add-by-place",
                    json={
                        "workspaceId": workspace_id,
                        "dayNo": day_no,
                        "placeId": place_id,
                    },
                )
                response.raise_for_status()
                return f"{day_no}일차 일정에 장소를 성공적으로 추가했습니다."
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                try:
                    error_message = e.response.json().get("message", e.response.text)
                except (ValueError, KeyError):
                    error_message = e.response.text
                return f"장소 추가 중 에러 발생: {error_message}"
            return (
                f"장소 추가 중 에러 발생: {e.response.status_code} - {e.response.text}"
            )
        except Exception as e:
            return f"장소 추가 중 에러 발생: {str(e)}"

    return [
        recommend_places_by_all_users,
        find_place_id_by_name,
        get_place_reviews,
        add_schedule_by_place,
    ]
