# 도구 응답 구조 리팩토링 요약

## 목표
**문제:** 장소 추천 도구들이 서로 다른 반환 구조를 가져 `place_extractor.py`가 복잡했음
- `recommend_popular_places_in_region`: `List[dict]` 또는 `str` (에러)
- `recommend_nearby_places`: `List[dict]` 또는 `str` (에러)
- `create_travel_route`: `dict` (항상, 에러는 내부 키)

**해결:** 모든 도구가 `ToolResult[T]` 표준 응답 형식을 반환하도록 통일

---

## 변경 사항

### 1. 표준 응답 DTO 생성 ✅
**파일:** `app/schemas/tool_response.py` (신규)

```python
class ToolResult(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    message: Optional[str] = None

class PlaceRecommendationData(BaseModel):
    places: List[dict]
    count: int

class TravelRouteData(BaseModel):
    total_days: int
    waypoints_count: int
    route: List[dict]

    @property
    def places(self) -> List[dict]:
        """route에서 모든 nearby_places를 평탄화"""
        return [place for wp in self.route
                for place in wp.get("nearby_places", [])]
```

**특징:**
- 모든 도구가 일관된 인터페이스 제공
- 성공/실패 구분이 명확
- 타입 안정성 확보

---

### 2. place_tool.py 업데이트 ✅
**파일:** `app/tools/place_tool.py`

**변경 전:**
```python
def recommend_popular_places_in_region(...):
    try:
        # ...
        return [place.model_dump() for place in place_responses]
    except ValueError as e:
        return str(e)  # 문자열 반환
    except Exception as e:
        return f"에러: {str(e)}"  # 문자열 반환
```

**변경 후:**
```python
def recommend_popular_places_in_region(...):
    try:
        # ...
        place_dicts = [place.model_dump() for place in place_responses]
        return ToolResult(
            success=True,
            data=PlaceRecommendationData(
                places=place_dicts,
                count=len(place_dicts)
            ),
            message=f"{region}에서 {len(place_dicts)}곳을 찾았습니다."
        ).model_dump()
    except ValueError as e:
        return ToolResult(
            success=False,
            error=f"지역명 검증 실패: {str(e)}"
        ).model_dump()
```

**적용 함수:**
- `recommend_popular_places_in_region` ✅
- `recommend_nearby_places` ✅

---

### 3. route_tool.py 업데이트 ✅
**파일:** `app/tools/route_tool.py`

**변경 전:**
```python
def create_travel_route(...):
    if not waypoints:
        return {"error": "경유지 없음", "route": []}

    # ...
    return response.model_dump()  # dict만 반환
```

**변경 후:**
```python
def create_travel_route(...):
    if not waypoints:
        return ToolResult(
            success=False,
            error="최소 1개 이상의 경유지를 지정해주세요."
        ).model_dump()

    # ...
    response_dict = response.model_dump()
    return ToolResult(
        success=True,
        data=TravelRouteData(**response_dict),
        message=f"{days}일 여행 코스를 생성했습니다."
    ).model_dump()
```

---

### 4. place_extractor.py 대폭 간소화 ✅
**파일:** `app/agent/utils/place_extractor.py`

**변경 전:** 118줄 (복잡한 분기 로직)
```python
# 장소 추천 도구 목록 하드코딩
PLACE_RECOMMENDATION_TOOLS = [...]

def is_place_recommendation_tool(tool_name: str) -> bool:
    return tool_name in PLACE_RECOMMENDATION_TOOLS

def extract_places_from_result(result, tool_name):
    if not is_place_recommendation_tool(tool_name):
        return []

    if tool_name == "create_travel_route":
        places = _extract_from_travel_route(result)
    else:
        places = _extract_from_place_list(result)
    # ...

def _extract_from_travel_route(result):
    # 복잡한 중첩 구조 파싱
    for waypoint in result.get("route", []):
        for place in waypoint.get("nearby_places", []):
            # ...

def _extract_from_place_list(result):
    # 리스트 파싱
    # ...
```

**변경 후:** 73줄 (단순 일관 처리)
```python
def extract_places_from_result(result: Any, tool_name: str) -> List[SimplePlace]:
    """
    모든 도구가 ToolResult[T] 형식으로 반환하므로 처리가 일관적
    """
    # 성공 여부 확인
    if not result.get("success", False):
        return []

    # data.places 추출
    data = result.get("data", {})
    places_data = data.get("places", [])

    # SimplePlace로 변환
    return [
        SimplePlace(id=p["id"], title=p["title"])
        for p in places_data
        if isinstance(p, dict) and "id" in p and "title" in p
    ]
```

**개선 효과:**
- **118줄 → 73줄** (38% 감소)
- 도구별 분기 로직 완전 제거
- 하드코딩된 도구 목록 제거
- 헬퍼 함수 2개 제거

---

### 5. update_state_node.py 간소화 ✅
**파일:** `app/agent/nodes/update_state_node.py`

**변경 전:**
```python
from app.agent.utils.place_extractor import (
    is_place_recommendation_tool,  # 불필요
    extract_places_from_result,
)

def update_state_node(state):
    # ...

    # 장소 추천 도구가 아니면 스킵
    if not is_place_recommendation_tool(tool_name):
        return {}

    # 장소 추출
    places = extract_places_from_result(content, tool_name)
```

**변경 후:**
```python
from app.agent.utils.place_extractor import extract_places_from_result

def update_state_node(state):
    """
    모든 장소 추천 도구가 ToolResult 형식으로 반환하므로
    처리 로직이 단순화됨
    """
    # ...

    # 장소 추출 (ToolResult 표준 형식 처리)
    places = extract_places_from_result(content, tool_name)
    # extractor 내부에서 success 확인하므로 별도 체크 불필요
```

---

### 6. 기타 수정 ✅
**파일:** `app/service/place_service.py`

**변경:**
```python
# 잘못된 import 경로 수정
- from service.crawling.review_service import ReviewService
+ from app.service.crawling.review_service import ReviewService
```

---

## LangGraph 설계 철학 준수

### 원칙
1. **도구는 순수 함수**: 상태를 변경하지 않고 결과만 반환
2. **노드가 상태 관리**: StateGraph의 노드가 상태를 읽고 쓰기
3. **일관된 인터페이스**: 모든 도구가 동일한 응답 구조 제공

### 현재 워크플로우
```
router → agent → tools → update_state → agent
                            ↓
                    도구 결과를 ToolResult로 반환
                            ↓
                    update_state_node가 파싱하여
                    last_recommended_places에 저장
```

### 장점
- ✅ **도구는 순수 함수로 유지** (상태 비저장)
- ✅ **상태 업데이트는 노드에서만** 발생
- ✅ **추출 로직이 극도로 단순**화됨
- ✅ **새 도구 추가 시 동일한 패턴** 사용
- ✅ **타입 안정성** 확보
- ✅ **에러 처리 일관성** 향상

---

## 테스트 결과

### 1. 단위 테스트 ✅
**파일:** `test_tool_refactoring.py`

```bash
$ uv run python test_tool_refactoring.py
==================================================
✅ 모든 테스트 통과!
==================================================
```

**테스트 케이스:**
- PlaceRecommendationData 성공/실패 케이스
- TravelRouteData 성공 케이스 + places 프로퍼티
- place_extractor 통합 테스트

### 2. 실제 도구 테스트 ✅
**파일:** `test_actual_tools.py`

```bash
$ uv run python test_actual_tools.py
==================================================
✅ 모든 테스트 완료!
==================================================
```

**테스트 결과:**
- `recommend_popular_places_in_region("서울", "맛집", 3)` → 3개 장소 추천 ✅
- `recommend_nearby_places("강남역", "카페", 2.0, 3)` → 3개 장소 추천 ✅
- `place_extractor` 통합 → 5개 장소 추출 ✅

---

## 파일 변경 요약

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `app/schemas/tool_response.py` | 신규 생성 | 표준 응답 DTO 정의 |
| `app/tools/place_tool.py` | 대폭 수정 | ToolResult 반환 구조로 변경 |
| `app/tools/route_tool.py` | 대폭 수정 | ToolResult 반환 구조로 변경 |
| `app/agent/utils/place_extractor.py` | 대폭 간소화 | 118줄 → 73줄 (38% 감소) |
| `app/agent/nodes/update_state_node.py` | 간소화 | 불필요한 체크 제거 |
| `app/service/place_service.py` | 버그 수정 | import 경로 수정 |
| `test_tool_refactoring.py` | 신규 생성 | 단위 테스트 |
| `test_actual_tools.py` | 신규 생성 | 통합 테스트 |

---

## 다음 단계 (선택사항)

### 1. 다른 도구들도 ToolResult로 마이그레이션
현재는 장소 추천 도구만 적용했지만, 다른 도구들도 동일한 패턴을 적용하면:
- `workspace_tool.py`의 도구들
- `poi_tool.py`의 도구들

### 2. 타입 힌트 추가
```python
def recommend_popular_places_in_region(...) -> dict:
    """항상 ToolResult.model_dump()를 반환"""
    ...
```

### 3. 에러 처리 강화
- 특정 에러 타입별로 더 구체적인 메시지 제공
- 재시도 로직 추가

---

## 결론

이번 리팩토링으로:
1. ✅ **복잡도 대폭 감소**: place_extractor 38% 코드 감소
2. ✅ **일관성 확보**: 모든 도구가 동일한 응답 구조
3. ✅ **타입 안정성**: Generic 타입으로 명확한 계약
4. ✅ **LangGraph 철학 준수**: 도구는 순수 함수, 노드가 상태 관리
5. ✅ **확장성 향상**: 새 도구 추가 시 동일한 패턴 적용
6. ✅ **유지보수성 향상**: 추출 로직이 한 곳에 집중

**설계가 깔끔해졌고, 근본적인 문제가 해결되었습니다!** 🎉
