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
    max_tokens=1000,
    disable_streaming=True
)

# no_llm = ChatBedrock(
#     # Amazon Nova Lite 모델 ID
#     model="global.anthropic.claude-sonnet-4-5-20250929-v1:0",#"anthropic.claude-3-haiku-20240307-v1:0",#bedrockConfig.BEDROCK_LLM_MODEL_ID, 
#     client=bedrock_client,
    
#     # [변경] Nova Lite (Titan 계열)에 맞는 model_kwargs 사용
#     model_kwargs={
#         "temperature": 0,
#         #"maxTokenCount": 10000,
#         "max_tokens": 10000, # max_tokens가 아님
#         #"anthropic_version": "bedrock-2023-05-31"
#     }
# )