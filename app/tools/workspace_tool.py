import httpx

from langchain_core.tools import tool

from app.common.config import nestJSConfig

BASE_URL = nestJSConfig.NESTJS_BACKEND_URL

def get_workspace_tools():
    """
    [워크스페이스 관련 도구 모음]
    """
    @tool
    def search_places(keyword: str):
        """
        지역명과 찾고 싶은 장소 키워드를 입력받아 장소를 검색합니다.
        예시: '강남역 맛집', '성수동 카페', '제주도 공항 근처 편의점'

        [답변 작성 규칙]
        1. 이 도구의 실행 결과(JSON)에는 x, y 좌표가 포함되어 있습니다.
        2. 하지만 사용자에게 답변할 때는 **절대 좌표(x, y)나 URL, ID를 말하지 마세요.** 
        3. 오직 **이름, 도로명 주소, 전화번호, 카테고리**만 사용하여 자연스럽게 요약해 주세요.
        """
        try:
            with httpx.Client() as client:
                # NestJS API 호출 (GET /places/search?keyword=...)
                response = client.get(
                    f"{BASE_URL}/workspace/search",
                    params={"keyword": keyword},
                )

                response.raise_for_status()

                # 검색 결과(JSON 리스트)를 문자열로 반환
                data = response.json()

                print(data)

                if not data:
                    return "검색 결과가 없습니다."
                
                # AI에게는 요약된 정보만 줘도 되지만,
                # 프론트엔드에는 전체 데이터(좌표 포함)가 tool_output으로 전달됨
                return str(data)
            
        except Exception as e:
            return f"검색 중 에러 발생: {str(e)}"
        
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
        
    return [search_places, recommend_places_by_all_users]

    