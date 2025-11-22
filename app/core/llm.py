# app/core/llm.py
import boto3
from langchain_aws import ChatBedrockConverse
from app.common.config import bedrockConfig

import sys

# 1. Bedrock 클라이언트 생성 (최초 1회 실행)
bedrock_client = boto3.client(
    "bedrock-runtime",
    region_name=bedrockConfig.AWS_REGION,
    aws_access_key_id=bedrockConfig.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=bedrockConfig.AWS_SECRET_ACCESS_KEY
)

# 2. 전역 LLM 객체 생성
# 다른 파일에서는 `from app.core.llm import global_llm`으로 가져다 쓰면 됩니다.
# ChatBedrockConverse는 Bedrock의 Converse API에 최적화되어 있어
# Tool Use(with_structured_output)와 같은 기능을 더 안정적으로 지원합니다.
global_llm = ChatBedrockConverse(
    model=bedrockConfig.BEDROCK_LLM_MODEL_ID, 
    client=bedrock_client,
    temperature=0,
    # ChatBedrockConverse는 max_tokens를 직접 파라미터로 받습니다.
    max_tokens=2048,
    disable_streaming=True
)
