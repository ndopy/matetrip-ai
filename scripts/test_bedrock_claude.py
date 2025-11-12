"""
AWS Bedrock Claude 3 Haiku 호출 테스트 스크립트

실행 방법:
    uv run python scripts/test_bedrock_claude.py
"""

import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.service.bedrock_llm_service import BedrockLLMService


def test_claude_basic():
    """기본 Claude 호출 테스트"""
    print("=" * 80)
    print("AWS Bedrock Claude 3 Haiku 테스트")
    print("=" * 80)

    try:
        llm_service = BedrockLLMService()
        print("\n✓ BedrockLLMService 초기화 성공")

        # 테스트 데이터
        test_reviews = [
            "경복궁 너무 좋았어요! 날씨도 좋고 사진 찍기 딱 좋았습니다. 한복 입고 가면 무료 입장이라 한복 대여해서 갔어요.",
            "가족들과 함께 방문했는데 아이들이 정말 좋아했어요. 경회루가 특히 아름다웠습니다.",
            "주말이라 사람이 많았지만 그래도 볼 만했어요. 역사 공부하기 좋은 곳입니다."
        ]
        place_title = "경복궁"

        print(f"\n[테스트 1] 태그 및 요약 생성")
        print(f"장소: {place_title}")
        print(f"리뷰 개수: {len(test_reviews)}개")
        print("-" * 80)

        result = llm_service.generate_tags_and_summary(test_reviews, place_title)

        if result:
            tags = result.get("tags", [])
            summary = result.get("summary", "")

            print(f"\n✓ Claude API 호출 성공!")
            print(f"\n생성된 태그: {tags}")
            print(f"\n생성된 요약:\n{summary}")

            if tags and summary:
                print("\n" + "=" * 80)
                print("✅ 테스트 성공! AWS Bedrock Claude가 정상적으로 동작합니다.")
                print("=" * 80)
                return True
            else:
                print("\n" + "=" * 80)
                print("⚠️  응답은 받았지만 태그/요약이 비어있습니다.")
                print("=" * 80)
                return False
        else:
            print("\n" + "=" * 80)
            print("❌ 응답을 받지 못했습니다.")
            print("=" * 80)
            return False

    except Exception as e:
        print(f"\n" + "=" * 80)
        print(f"❌ 테스트 실패!")
        print(f"오류: {e}")
        print("=" * 80)

        if "ResourceNotFoundException" in str(e):
            print("\n해결 방법:")
            print("1. AWS Console → Amazon Bedrock → Model access")
            print("2. 'Manage model access' 클릭")
            print("3. 'Anthropic Claude 3 Haiku' 체크")
            print("4. 'Request model access' 클릭")
            print("5. Use case details 작성 후 제출")
            print("6. 승인까지 약 15분 소요")

        return False


def test_categories():
    """카테고리 생성 테스트"""
    print("\n" + "=" * 80)
    print("[테스트 2] 카테고리 생성")
    print("=" * 80)

    try:
        llm_service = BedrockLLMService()

        test_reviews = [
            "여기 파스타가 정말 맛있어요! 까르보나라 추천합니다.",
            "분위기도 좋고 직원분들이 친절하세요. 데이트하기 좋은 곳입니다.",
            "이탈리안 레스토랑인데 가격대비 훌륭해요."
        ]
        place_title = "파스타 맛집"

        print(f"장소: {place_title}")
        print(f"리뷰 개수: {len(test_reviews)}개")
        print("-" * 80)

        categories = llm_service.generate_categories_from_reviews(
            test_reviews, place_title, kakao_category="음식점>이탈리안"
        )

        if categories:
            print(f"\n✓ 카테고리 생성 성공!")
            print(f"생성된 카테고리: {categories}")
            return True
        else:
            print(f"\n⚠️  카테고리가 비어있습니다.")
            return False

    except Exception as e:
        print(f"\n❌ 카테고리 생성 실패: {e}")
        return False


if __name__ == "__main__":
    print("\n🚀 AWS Bedrock Claude 테스트 시작\n")

    # 테스트 1: 태그 및 요약 생성
    test1_success = test_claude_basic()

    # 테스트 2: 카테고리 생성
    test2_success = test_categories()

    # 최종 결과
    print("\n" + "=" * 80)
    print("최종 테스트 결과")
    print("=" * 80)
    print(f"1. 태그/요약 생성: {'✅ 성공' if test1_success else '❌ 실패'}")
    print(f"2. 카테고리 생성: {'✅ 성공' if test2_success else '❌ 실패'}")
    print("=" * 80)

    if test1_success and test2_success:
        print("\n🎉 모든 테스트 통과! Bedrock Claude가 정상 작동합니다.")
    else:
        print("\n⚠️  일부 테스트 실패. 위의 오류 메시지를 확인하세요.")
