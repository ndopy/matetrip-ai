"""
경로 최적화 API 테스트 스크립트

사용법:
    uv run python scripts/test_route_optimization.py
"""

import httpx
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(str(Path(__file__).parent.parent))


async def test_simple_optimization():
    """간단한 경로 최적화 테스트"""
    print("\n" + "=" * 60)
    print("📍 테스트 1: 간단한 경로 최적화 (브로드캐스트 없음)")
    print("=" * 60)

    url = "http://localhost:8000/optimization/route"

    # 서울 강남 지역의 실제 좌표 예시
    payload = {
        "poi_list": [
            {
                "id": "gangnam-station",
                "longitude": 127.0276,
                "latitude": 37.4979
            },
            {
                "id": "coex",
                "longitude": 127.0594,
                "latitude": 37.5126
            },
            {
                "id": "bongeunsa",
                "longitude": 127.0566,
                "latitude": 37.5147
            },
            {
                "id": "seolleung",
                "longitude": 127.0487,
                "latitude": 37.5044
            }
        ]
    }

    try:
        async with httpx.AsyncClient() as client:
            print("\n🔄 API 요청 중...")
            response = await client.post(url, json=payload, timeout=60.0)

            if response.status_code != 200:
                print(f"❌ 에러 발생: {response.status_code}")
                print(response.text)
                return

            result = response.json()

            print("\n✅ 최적화 완료!")
            print(f"\n📊 결과:")
            print(f"  - 총 소요시간: {result['total_duration']}초 ({result['total_duration'] / 60:.1f}분)")
            print(f"  - 총 거리: {result['total_distance']}미터 ({result['total_distance'] / 1000:.2f}km)")
            print(f"\n🗺️  최적 경로:")
            for i, poi in enumerate(result['optimized_poi_order'], 1):
                print(f"  {i}. {poi['id']} (경도: {poi['longitude']}, 위도: {poi['latitude']})")

    except httpx.ConnectError:
        print("❌ 서버에 연결할 수 없습니다. FastAPI 서버가 실행 중인지 확인하세요.")
        print("   실행 명령: uv run python main.py")
    except Exception as e:
        print(f"❌ 에러 발생: {e}")


async def test_fixed_start_end():
    """시작/종료 지점 고정 최적화 테스트"""
    print("\n" + "=" * 60)
    print("📍 테스트 2: 시작/종료 지점 고정 (호텔 왕복)")
    print("=" * 60)

    url = "http://localhost:8000/optimization/route"

    payload = {
        "poi_list": [
            {
                "id": "hotel",
                "longitude": 127.0276,
                "latitude": 37.4979
            },
            {
                "id": "restaurant",
                "longitude": 127.0594,
                "latitude": 37.5126
            },
            {
                "id": "museum",
                "longitude": 127.0566,
                "latitude": 37.5147
            },
            {
                "id": "cafe",
                "longitude": 127.0487,
                "latitude": 37.5044
            }
        ],
        "start_index": 0,  # 호텔에서 시작
        "end_index": 0     # 호텔로 돌아옴
    }

    try:
        async with httpx.AsyncClient() as client:
            print("\n🔄 API 요청 중...")
            response = await client.post(url, json=payload, timeout=60.0)

            if response.status_code != 200:
                print(f"❌ 에러 발생: {response.status_code}")
                print(response.text)
                return

            result = response.json()

            print("\n✅ 최적화 완료!")
            print(f"\n📊 결과:")
            print(f"  - 총 소요시간: {result['total_duration']}초 ({result['total_duration'] / 60:.1f}분)")
            print(f"  - 총 거리: {result['total_distance']}미터 ({result['total_distance'] / 1000:.2f}km)")
            print(f"\n🗺️  최적 경로:")
            for i, poi in enumerate(result['optimized_poi_order'], 1):
                print(f"  {i}. {poi['id']}")

            # 시작과 끝이 같은지 확인
            if result['optimized_poi_order'][0]['id'] == result['optimized_poi_order'][-1]['id']:
                print("\n✅ 시작 지점으로 돌아왔습니다!")

    except httpx.ConnectError:
        print("❌ 서버에 연결할 수 없습니다. FastAPI 서버가 실행 중인지 확인하세요.")
    except Exception as e:
        print(f"❌ 에러 발생: {e}")


async def test_broadcast():
    """NestJS 브로드캐스트 테스트"""
    print("\n" + "=" * 60)
    print("📍 테스트 3: 경로 최적화 + NestJS 브로드캐스트")
    print("=" * 60)

    url = "http://localhost:8000/optimization/route/broadcast"

    payload = {
        "workspace_id": "test-workspace-123",
        "plan_day_id": "test-plan-day-456",
        "poi_list": [
            {
                "id": "poi-1",
                "longitude": 127.0276,
                "latitude": 37.4979
            },
            {
                "id": "poi-2",
                "longitude": 127.0594,
                "latitude": 37.5126
            },
            {
                "id": "poi-3",
                "longitude": 127.0566,
                "latitude": 37.5147
            }
        ]
    }

    try:
        async with httpx.AsyncClient() as client:
            print("\n🔄 API 요청 중...")
            response = await client.post(url, json=payload, timeout=60.0)

            if response.status_code != 200:
                print(f"❌ 에러 발생: {response.status_code}")
                print(response.text)
                return

            result = response.json()

            print("\n✅ 최적화 완료!")
            print(f"\n📊 결과:")
            print(f"  - 총 소요시간: {result['total_duration']}초")
            print(f"  - 총 거리: {result['total_distance']}미터")

            if result['success']:
                print(f"\n✅ NestJS 브로드캐스트 성공!")
                print(f"  응답: {result.get('nestjs_response')}")
            else:
                print(f"\n⚠️  NestJS 브로드캐스트 실패")
                print(f"  에러: {result.get('error')}")

            print(f"\n🗺️  최적 경로:")
            for i, poi in enumerate(result['optimized_poi_order'], 1):
                print(f"  {i}. {poi['id']}")

    except httpx.ConnectError:
        print("❌ 서버에 연결할 수 없습니다. FastAPI 서버가 실행 중인지 확인하세요.")
    except Exception as e:
        print(f"❌ 에러 발생: {e}")


async def main():
    """모든 테스트 실행"""
    print("\n" + "=" * 60)
    print("🚀 경로 최적화 API 테스트 시작")
    print("=" * 60)

    print("\n⚠️  주의사항:")
    print("  1. FastAPI 서버가 실행 중이어야 합니다: uv run python main.py")
    print("  2. .env 파일에 KAKAO_MOBILITY_API_KEY가 설정되어 있어야 합니다")
    print("  3. 테스트 3번은 NestJS 서버가 필요합니다 (선택)")

    input("\n계속하려면 Enter를 누르세요...")

    # 테스트 1: 간단한 최적화
    await test_simple_optimization()

    await asyncio.sleep(2)

    # 테스트 2: 시작/종료 고정
    await test_fixed_start_end()

    await asyncio.sleep(2)

    # 테스트 3: 브로드캐스트 (선택)
    print("\n" + "=" * 60)
    choice = input("\nNestJS 브로드캐스트 테스트를 실행하시겠습니까? (y/n): ")
    if choice.lower() == 'y':
        await test_broadcast()

    print("\n" + "=" * 60)
    print("✅ 모든 테스트 완료!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
