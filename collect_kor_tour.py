# collect_kor_tour.py
from __future__ import annotations

import os
import json
from datetime import datetime
import time
from typing import Iterator, List, Optional

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator


# =====================
# 1) 설정
# =====================

BASE_URL = "https://apis.data.go.kr/B551011/KorService2"
# 실제로는 .env 에 두고 불러오는 걸 추천
def _required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None:
        raise RuntimeError(f"환경 변수 {name} 가 설정되어 있어야 합니다.")
    return value


SERVICE_KEY = _required_env("SECRET_KEY")


# =====================
# 2) 응답 모델 정의
# =====================


class AreaBasedItem(BaseModel):
    """
    areaBasedList2 에서 item 하나에 해당.
    실제 필드는 훨씬 많은데, 예시로 자주 쓰는 것 몇 개만 넣어둠.
    """

    # 기본 설정 : model_config = ConfigDict(extra="ignore")

    contentid: Optional[int] = None
    title: Optional[str] = None
    addr1: Optional[str] = None
    addr2: Optional[str] = None
    areacode: Optional[int] = None
    sigungucode: Optional[int] = None
    contenttypeid: Optional[int] = None
    cat1: Optional[str] = None
    cat2: Optional[str] = None
    cat3: Optional[str] = None
    booktour: Optional[str] = None
    firstimage: Optional[str] = None
    firstimage2: Optional[str] = None
    cpyrhtDivCd: Optional[str] = None
    mapx: Optional[float] = None
    mapy: Optional[float] = None
    mlevel: Optional[int] = None
    tel: Optional[str] = None
    zipcode: Optional[str] = None
    createdtime: Optional[str] = None
    modifiedtime: Optional[str] = None

    @field_validator(
        "contentid",
        "areacode",
        "sigungucode",
        "contenttypeid",
        "mlevel",
        mode="before",
    )
    @classmethod
    def _normalize_int_fields(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            if value == "":
                return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @field_validator("mapx", "mapy", mode="before")
    @classmethod
    def _normalize_float_fields(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            if value == "":
                return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None


class AreaBasedBody(BaseModel):
    items: dict = Field(default_factory=dict)
    numOfRows: int
    pageNo: int
    totalCount: int

    @field_validator("items", mode="before")
    @classmethod
    def _normalize_items(cls, value):
        if value in (None, "", []):
            return {}
        if isinstance(value, dict):
            return value
        if isinstance(value, list):
            return {"item": value}
        raise TypeError("items must be a dict, list, empty string, or null")

    def get_items(self) -> List[AreaBasedItem]:
        raw_items = self.items.get("item") or []
        # item 이 dict 하나일 때도, 리스트일 때도 있어서 일관되게 리스트로 맞춰줌
        if isinstance(raw_items, dict):
            raw_items = [raw_items]
        return [AreaBasedItem.model_validate(i) for i in raw_items]


class AreaBasedResponse(BaseModel):
    body: AreaBasedBody


class KorTourResponse(BaseModel):
    response: AreaBasedResponse


# =====================
# 3) API 클라이언트
# =====================


class KorTourApiClient:
    def __init__(
        self,
        service_key: str,
        app_name: str = "AppTest",
        *,
        max_retries: int = 7,
        backoff_factor: float = 0.5,
        request_interval: float = 0.3,
    ) -> None:
        self.service_key = service_key
        self.app_name = app_name
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.request_interval = request_interval
        # 필요하면 여기서 proxies, timeout 등도 설정
        self.client = httpx.Client(timeout=10.0)

    def _get(self, path: str, params: dict) -> KorTourResponse:
        url = f"{BASE_URL}/{path}"
        # 공통 쿼리 파라미터
        base_params = {
            "serviceKey": self.service_key,
            "MobileOS": "ETC",
            "MobileApp": self.app_name,
            "_type": "json",
        }
        merged = {**base_params, **params}
        backoff = self.backoff_factor
        for attempt in range(self.max_retries):
            res = self.client.get(url, params=merged)
            try:
                res.raise_for_status()
                data = res.json()
                return KorTourResponse.model_validate(data)
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status == 429 and attempt < self.max_retries - 1:
                    retry_after = exc.response.headers.get("Retry-After")
                    try:
                        delay = float(retry_after)
                    except (TypeError, ValueError):
                        delay = backoff
                    print(
                        f"[KorTourApiClient] 429 Too Many Requests, retrying in {delay} sec..."
                    )
                    time.sleep(delay)
                    backoff *= 2
                    continue
                raise
        raise RuntimeError("KorTour API request failed after retries")

    def get_area_based_list(
        self,
        *,
        area_code: int,
        page_no: int = 1,
        num_rows: int = 10,
        arrange: str = "A",
    ) -> AreaBasedBody:
        """
        areaBasedList2 한 페이지 조회
        """
        params = {
            "areaCode": area_code,
            "pageNo": page_no,
            "numOfRows": num_rows,
            "arrange": arrange,  # A: 제목순, B: 조회순 등
        }
        kor_res = self._get("areaBasedList2", params)
        return kor_res.response.body

    def iter_area_based_all(
        self,
        *,
        area_code: int,
        num_rows: int = 20,
        arrange: str = "A",
    ) -> Iterator[AreaBasedItem]:
        """
        페이지를 자동으로 돌면서 전체 아이템을 yield
        """
        page = 1
        while True:
            body = self.get_area_based_list(
                area_code=area_code,
                page_no=page,
                num_rows=num_rows,
                arrange=arrange,
            )
            items = body.get_items()
            if not items:
                break

            for item in items:
                yield item

            # 마지막 페이지 판단
            if body.pageNo * body.numOfRows >= body.totalCount:
                break

            if self.request_interval > 0:
                time.sleep(self.request_interval)
            page += 1


# =====================
# 4) 수집 로직
# =====================


def collect_area_data(area_code: int) -> list[dict]:
    client = KorTourApiClient(SERVICE_KEY)
    results: list[dict] = []

    for item in client.iter_area_based_all(area_code=area_code, num_rows=1):
        # dict 로 변환해서 저장
        results.append(item.model_dump())

    return results


def save_as_json(data: list[dict], filename: str) -> None:
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    AREA_CODE = 32  # 인천 (예시)
    items = collect_area_data(AREA_CODE)
    print(f"수집된 개수: {len(items)}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"area_{AREA_CODE}_{ts}.json"
    save_as_json(items, filename)
    print(f"저장 완료: {filename}")
