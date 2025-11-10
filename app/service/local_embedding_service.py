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
        """
        if len(texts) <= 0:
            return []

        try:
            embeddings = []

            # AWS Bedrock은 배치를 지원하지 않으므로 각 텍스트마다 개별 호출
            for text in texts:
                # Amazon Titan Embeddings 요청 body
                body = json.dumps({"inputText": text})

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
                    log.error(f"임베딩 생성 실패: {text[:50]}...")
                    raise ValueError("임베딩 응답이 비어있습니다")

            log.info(f"\n[배치 임베딩 완료]")
            log.info(f"[생성된 임베딩 개수]: {len(embeddings)}")
            log.info(f"[임베딩 차원]: {len(embeddings[0]) if embeddings else 0}\n")

            return embeddings

        except Exception as e:
            log.error(f"Error creating embeddings: {e}")
            raise
