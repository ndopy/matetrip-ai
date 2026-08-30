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
    max_tokens=2048,
)
