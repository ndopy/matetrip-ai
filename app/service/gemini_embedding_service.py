import logging
from typing import List

import numpy as np
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.common.config import geminiConfig

log = logging.getLogger(__name__)


class GeminiEmbeddingService:
    """
    Google Gemini를 사용한 임베딩 서비스 (AWS Bedrock Titan 대체)
    BedrockEmbeddingService와 동일한 인터페이스를 제공한다.
    """

    def __init__(self):
        log.info(f"\n[Gemini 임베딩 서비스 초기화]")
        log.info(f"Model ID: {geminiConfig.GEMINI_EMBEDDING_MODEL_ID}")
        log.info(f"Output Dim: {geminiConfig.GEMINI_EMBEDDING_DIM}\n")

        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=geminiConfig.GEMINI_EMBEDDING_MODEL_ID,
            google_api_key=geminiConfig.GOOGLE_API_KEY,
            output_dimensionality=geminiConfig.GEMINI_EMBEDDING_DIM,
        )
        log.info("[Gemini 임베딩 서비스 초기화 완료]\n")

    def create_embedding(self, text: str) -> List[float]:
        """
        단일 텍스트를 받아서 임베딩 벡터를 반환
        """
        if not text or len(text.strip()) == 0:
            raise ValueError("텍스트가 비어있습니다")

        try:
            embedding = self.embeddings.embed_query(text)
            normalized = self._normalize(embedding)
            log.info(f"임베딩 생성 완료 (차원: {len(normalized)})")
            return normalized
        except Exception as e:
            log.error(f"Error creating embedding: {e}")
            raise

    def create_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        텍스트 배열을 받아서 임베딩 벡터 배열을 반환
        """
        if len(texts) <= 0:
            return []

        try:
            raw_embeddings = self.embeddings.embed_documents(texts)
            embeddings = [self._normalize(e) for e in raw_embeddings]

            log.info(f"\n[배치 임베딩 완료]")
            log.info(f"[생성된 임베딩 개수]: {len(embeddings)}")
            log.info(f"[임베딩 차원]: {len(embeddings[0]) if embeddings else 0}\n")

            return embeddings
        except Exception as e:
            log.error(f"Error creating embeddings: {e}")
            raise

    def _normalize(self, embedding: List[float]) -> List[float]:
        """
        gemini-embedding-001은 3072차원 미만으로 자르면 단위 벡터가 아니게 되므로,
        pgvector 코사인 거리(<=>) 계산이 정확하도록 L2 정규화를 직접 해줘야 한다.
        """
        vector = np.array(embedding)
        norm = np.linalg.norm(vector)
        if norm == 0:
            return embedding
        return (vector / norm).tolist()
