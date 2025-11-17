from app.util.tieme_meter import timeMeter
from .workspace_tool import get_workspace_tools
from .place_tool import get_place_tools


@timeMeter
def create_nest_tools():
    """
    user_token: 쿠키에서 추출한 순수 JWT 문자열
    """
    # (만약 NestJS가 '무조건 쿠키로만' 인증을 받게 설정되어 있다면
    # 위 Authorization 줄을 지우고 아래 주석을 해제하세요)
    # headers = {"Cookie": f"access_token={user_token}"}

    # 모든 도구 리스트 합치기
    all_tools = []

    # 리스트 더하기
    all_tools.extend(get_workspace_tools())
    all_tools.extend(get_place_tools())

    return all_tools
