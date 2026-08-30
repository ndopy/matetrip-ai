# app/core/llm.py
from langchain_google_genai import ChatGoogleGenerativeAI
from app.common.config import geminiConfig

# 전역 LLM 객체 생성
# 다른 파일에서는 `from app.core.llm import global_llm`으로 가져다 쓰면 됩니다.
# 원래는 AWS Bedrock(ChatBedrockConverse)을 썼으나, 배포 계정의 Bedrock 크레딧이
# 사라져서 포트폴리오 로컬 데모용으로 무료 Gemini API로 교체했습니다.
global_llm = ChatGoogleGenerativeAI(
    model=geminiConfig.GEMINI_LLM_MODEL_ID,
    google_api_key=geminiConfig.GOOGLE_API_KEY,
    temperature=0,
    # Gemini 3.x 계열은 답변 전 내부 reasoning에도 max_tokens 예산을 함께 쓰고,
    # max_tokens를 올려도 reasoning이 그만큼 늘어나 실제 답변 text가 빈 문자열로
    # 잘리는 현상이 있었다(경복궁 볼거리 추천 시나리오에서 reasoning이 1963 →
    # 3481 tokens까지 늘어나며 재현). thinking_level="low"로 reasoning 깊이 자체를
    # 낮춰 답변 text가 안정적으로 생성되게 한다.
    thinking_level="low",
    max_tokens=4096,
)
