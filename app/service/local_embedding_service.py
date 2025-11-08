from ast import Tuple
import logging
from typing import List

from sentence_transformers import SentenceTransformer
from app.common.config import embeddingConfig

log = logging.getLogger(__name__)


class LocalEmbeddingService:
    """
    (임시)
    Sentence Transformers를 사용한 로컬 임베딩 서비스
    """

    # def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
    def __init__(self):
        local_model_name = embeddingConfig.LOCAL_EMBEDDING_MODEL
        log.info(f"\n[로컬 임베딩 모델 로딩]")
        log.info(f"로컬 임베딩 모델명: {local_model_name}\n")

        self.model = SentenceTransformer(local_model_name)
        self.model_name = local_model_name
        log.info("[로컬 임베딩 모델 로딩 완료]\n")
        log.info(f"임베딩 차원 : {self.model.get_sentence_embedding_dimension()}\n")

    def create_embedding(self, text: str) -> List[float]:

        return []

    def create_embeddings_batch(self, texts: List[str]) -> List[List[float]]:

        if len(texts) <= 0:
            return []
        try:
            # show_progress_bar : 진행률 표시
            # convert_to_numpy : 결과가 PyTorch 텐서가 아니라 NumPy 배열(ndarray)로 변환
            embedding_array = self.model.encode(
                texts, convert_to_numpy=True, show_progress_bar=True
            )
            embeddingList = [embedding.tolist() for embedding in embedding_array]
            log.info(f"\n[배치 임베딩 완료]")
            log.info(f"\n[생성된 임베딩 개수] : {len(embeddingList)}")
            return embeddingList

        except Exception as e:
            log.error(f"Error creating embeddings: {e}")
            raise
