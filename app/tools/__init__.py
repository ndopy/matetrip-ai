from .workspace_tool import get_search_tools

def create_nest_tools(user_token: str):
    """
    user_token: 쿠키에서 추출한 순수 JWT 문자열
    """
    
    # -------------------------------------------------------------
    # [중요] NestJS AuthGuard('jwt')를 통과하기 위한 헤더 설정
    # -------------------------------------------------------------
    headers = {
        # 보통 API 통신에서는 Bearer 방식을 가장 많이 씁니다.
        "Authorization": f"Bearer {user_token}",
        
        "Content-Type": "application/json"
    }
    
    # (만약 NestJS가 '무조건 쿠키로만' 인증을 받게 설정되어 있다면 
    # 위 Authorization 줄을 지우고 아래 주석을 해제하세요)
    # headers = {"Cookie": f"access_token={user_token}"}

    # 모든 도구 리스트 합치기
    all_tools = []

    # 리스트 더하기
    all_tools.extend(get_search_tools(headers))

    return all_tools