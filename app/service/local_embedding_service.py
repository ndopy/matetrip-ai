import json
import logging
from typing import List

import boto3
from app.common.config import bedrockConfig

log = logging.getLogger(__name__)


class BedrockEmbeddingService:
    """
    AWS Bedrock을 사용한 임베딩 서비스
    Amazon Titan Embeddings 모델 사용
    """

    def __init__(self):
        log.info(f"\n[AWS Bedrock 임베딩 서비스 초기화]")
        log.info(f"AWS Region: {bedrockConfig.AWS_REGION}")
        log.info(f"Model ID: {bedrockConfig.MODEL_ID}\n")

        # AWS Bedrock Runtime 클라이언트 생성
        self.bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=bedrockConfig.AWS_REGION,
            aws_access_key_id=bedrockConfig.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=bedrockConfig.AWS_SECRET_ACCESS_KEY,
        )
        self.model_id = bedrockConfig.MODEL_ID
        log.info("[AWS Bedrock 임베딩 서비스 초기화 완료]\n")

    def create_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        텍스트 배열을 받아서 임베딩 벡터 배열을 반환
        AWS Bedrock Titan 임베딩 모델: 최대 8192 토큰 제한
        """
        if len(texts) <= 0:
            return []

        try:
            embeddings = []

            # AWS Bedrock은 배치를 지원하지 않으므로 각 텍스트마다 개별 호출
            for idx, text in enumerate(texts):
                # 토큰 제한 처리: 안전하게 5000자로 제한 (약 6000-7000 토큰)
                truncated_text = self._truncate_text(text, max_length=5000)

                if len(text) != len(truncated_text):
                    log.warning(
                        f"텍스트 {idx+1}번이 너무 길어서 잘렸습니다. "
                        f"원본: {len(text)}자 → 자른 후: {len(truncated_text)}자"
                    )

                # Amazon Titan Embeddings 요청 body
                body = json.dumps({"inputText": truncated_text})

                # Bedrock API 호출
                response = self.bedrock_runtime.invoke_model(
                    modelId=self.model_id,
                    body=body,
                    contentType="application/json",
                    accept="application/json",
                )

                # 응답 파싱
                response_body = json.loads(response["body"].read())
                embedding = response_body.get("embedding")

                if embedding:
                    embeddings.append(embedding)
                else:
                    log.error(
                        f"임베딩 생성 실패: 텍스트 길이 {len(truncated_text)}, 인덱스 {len(embeddings)}"
                    )
                    raise ValueError("임베딩 응답이 비어있습니다")

            log.info(f"\n[배치 임베딩 완료]")
            log.info(f"[생성된 임베딩 개수]: {len(embeddings)}")
            log.info(f"[임베딩 차원]: {len(embeddings[0]) if embeddings else 0}\n")

            return embeddings

        except Exception as e:
            log.error(f"Error creating embeddings: {e}")
            raise

    def _truncate_text(self, text: str, max_length: int = 5000) -> str:
        """
        텍스트를 최대 길이로 자릅니다.
        AWS Bedrock Titan 임베딩 모델은 최대 8192 토큰을 지원하므로
        안전하게 5000자(약 6000-7000 토큰)로 제한합니다.

        Args:
            text: 원본 텍스트
            max_length: 최대 문자 수

        Returns:
            잘린 텍스트
        """
        if len(text) <= max_length:
            return text

        # 문장 단위로 자르기 (마지막 문장이 잘리지 않도록)
        truncated = text[:max_length]

        # 마지막 마침표, 느낌표, 물음표 위치 찾기
        last_sentence_end = max(
            truncated.rfind('.'),
            truncated.rfind('!'),
            truncated.rfind('?'),
            truncated.rfind('。'),  # 일본어
            truncated.rfind('．'),
        )

        # 문장 끝을 찾았으면 그 위치까지만
        if last_sentence_end > max_length * 0.8:  # 80% 이상 위치에서 찾은 경우만
            return truncated[:last_sentence_end + 1]

        # 못 찾았으면 그냥 자르기
        return truncated
