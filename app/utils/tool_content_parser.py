"""
도구 응답 content 파싱 유틸리티

후처리 노드에서 공통적으로 사용하는 JSON 파싱 로직을 제공합니다.
"""

import json
from typing import Any, Optional


def parse_tool_content(
    content: Any, allow_error_messages: bool = False
) -> Optional[dict]:
    """
    도구 응답 content를 파싱하여 dict로 반환합니다.
    Args:
        content: 도구 응답 content (str 또는 dict)
        allow_error_messages: True면 에러 메시지 문자열도 허용 (기본값: False)

    Returns:
        파싱된 dict 또는 None (파싱 실패 시)
    """
    if not content:
        return None

    # 이미 dict인 경우 그대로 반환
    if isinstance(content, dict):
        return content

    # 문자열인 경우 JSON 파싱 시도
    if isinstance(content, str):
        # 빈 문자열 체크
        if not content.strip():
            return None

        # 에러 메시지 체크 (allow_error_messages=False일 때만)
        if not allow_error_messages:
            if "에러" in content or "찾지 못했습니다" in content:
                return None

        # JSON 파싱 시도
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return None

    # dict도 str도 아닌 경우
    return None
