"""
AWS Bedrock Titan Embedding 모델 테스트 스크립트

실행 방법:
    uv run python scripts/test_bedrock_embedding.py
"""

import sys
import os
from app.service.bedrock_embedding_service import BedrockEmbeddingService

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_single_embedding():
    """단일 텍스트 임베딩 테스트"""
    print("=" * 80)
    print("AWS Bedrock Titan Embedding 테스트")
    print("=" * 80)

    try:
        embedding_service = BedrockEmbeddingService()
        print("\n✓ BedrockEmbeddingService 초기화 성공")

        # 테스트 텍스트
        test_text = "경복궁은 조선시대의 대표적인 궁궐로, 서울의 주요 관광 명소입니다."

        print(f"\n[테스트 1] 단일 텍스트 임베딩")
        print(f"입력 텍스트: {test_text}")
        print("-" * 80)

        embedding = embedding_service.create_embedding(test_text)

        if embedding and len(embedding) > 0:
            print(f"\n✓ 임베딩 생성 성공!")
            print(f"임베딩 차원: {len(embedding)}")
            print(f"임베딩 미리보기 (처음 5개): {embedding[:5]}")
            print(f"임베딩 타입: {type(embedding[0])}")

            print("\n" + "=" * 80)
            print("✅ 테스트 성공! Bedrock Titan Embedding이 정상 작동합니다.")
            print("=" * 80)
            return True
        else:
            print("\n" + "=" * 80)
            print("❌ 임베딩이 비어있습니다.")
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
            print("3. 'Amazon Titan Embeddings G1 - Text' 체크")
            print("4. 'Save changes' 클릭")

        return False


def test_batch_embedding():
    """배치 텍스트 임베딩 테스트"""
    print("\n" + "=" * 80)
    print("[테스트 2] 배치 임베딩")
    print("=" * 80)

    try:
        embedding_service = BedrockEmbeddingService()

        test_texts = [
            "경복궁은 서울의 대표적인 관광지입니다.",
            "남산타워에서 보는 야경이 아름답습니다.",
            "북촌한옥마을은 전통 한옥이 잘 보존되어 있습니다.",
        ]

        print(f"입력 텍스트 개수: {len(test_texts)}개")
        print("-" * 80)

        embeddings = embedding_service.create_embeddings_batch(test_texts)

        if embeddings and len(embeddings) == len(test_texts):
            print(f"\n✓ 배치 임베딩 생성 성공!")
            print(f"생성된 임베딩 개수: {len(embeddings)}")
            print(f"각 임베딩 차원: {len(embeddings[0])}")

            # 두 임베딩 간 코사인 유사도 계산
            import numpy as np

            def cosine_similarity(a, b):
                return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

            sim_0_1 = cosine_similarity(
                np.array(embeddings[0]), np.array(embeddings[1])
            )
            sim_0_2 = cosine_similarity(
                np.array(embeddings[0]), np.array(embeddings[2])
            )

            print(f"\n유사도 분석:")
            print(f"  경복궁 vs 남산타워: {sim_0_1:.4f}")
            print(f"  경복궁 vs 북촌한옥마을: {sim_0_2:.4f}")

            return True
        else:
            print(
                f"\n⚠️  임베딩 개수가 맞지 않습니다. (예상: {len(test_texts)}, 실제: {len(embeddings)})"
            )
            return False

    except Exception as e:
        print(f"\n❌ 배치 임베딩 실패: {e}")
        return False


def test_long_text_truncation():
    """긴 텍스트 자르기 테스트"""
    print("\n" + "=" * 80)
    print("[테스트 3] 긴 텍스트 처리")
    print("=" * 80)

    try:
        embedding_service = BedrockEmbeddingService()

        # 긴 텍스트 생성 (6000자)
        long_text = "경복궁은 조선시대의 대표적인 궁궐입니다. " * 200

        print(f"입력 텍스트 길이: {len(long_text)}자")
        print("-" * 80)

        embedding = embedding_service.create_embedding(long_text)

        if embedding:
            print(f"\n✓ 긴 텍스트 임베딩 성공!")
            print(f"임베딩 차원: {len(embedding)}")
            print(f"(자동으로 5000자로 잘렸을 것입니다)")
            return True
        else:
            print(f"\n❌ 긴 텍스트 임베딩 실패")
            return False

    except Exception as e:
        print(f"\n❌ 긴 텍스트 처리 실패: {e}")
        return False


if __name__ == "__main__":
    print("\n🚀 AWS Bedrock Titan Embedding 테스트 시작\n")

    # 테스트 1: 단일 임베딩
    test1_success = test_single_embedding()

    # 테스트 2: 배치 임베딩
    test2_success = test_batch_embedding()

    # 테스트 3: 긴 텍스트 처리
    test3_success = test_long_text_truncation()

    # 최종 결과
    print("\n" + "=" * 80)
    print("최종 테스트 결과")
    print("=" * 80)
    print(f"1. 단일 임베딩: {'✅ 성공' if test1_success else '❌ 실패'}")
    print(f"2. 배치 임베딩: {'✅ 성공' if test2_success else '❌ 실패'}")
    print(f"3. 긴 텍스트 처리: {'✅ 성공' if test3_success else '❌ 실패'}")
    print("=" * 80)

    if test1_success and test2_success and test3_success:
        print("\n🎉 모든 테스트 통과! Bedrock Titan Embedding이 정상 작동합니다.")
    else:
        print("\n⚠️  일부 테스트 실패. 위의 오류 메시지를 확인하세요.")
