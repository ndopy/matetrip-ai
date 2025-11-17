from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
    DB_HOST: str = Field(default="localhost")
    DB_PORT: int = Field(default=5432)
    DB_USER: str = Field(default="")
    DB_PASSWORD: str = Field(default="")
    DB_NAME: str = Field(default="")
    DB_DEBUG: bool = Field(default=False)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def sync_db_url(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


class NaverSearchConfig(BaseSettings):
    NAVER_CLIENT_ID: str = Field(default="")
    NAVER_CLIENT_SECRET: str = Field(default="")
    NAVER_BLOG_SEARCH_URL: str = Field(default="")
    NAVER_IMAGE_SEARCH_URL: str = Field(
        default="https://openapi.naver.com/v1/search/image"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class EmbeddingConfig(BaseSettings):
    LOCAL_EMBEDDING_MODEL: str = Field(
        default="jhgan/ko-sroberta-multitask",
        description="SentenceTransformer model name for local embeddings",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class OpenAIConfig(BaseSettings):
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API Key")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini", description="OpenAI Model")
    OPENAI_EMBEDDING_MODEL: str = Field(
        default="text-embedding-3-small", description="OpenAI Embedding Model"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class BedRockConfig(BaseSettings):
    AWS_REGION: str = Field(default="us-east-1", description="AWS Region")
    BEDROCK_EMBEDDING_MODEL_ID: str = Field(
        default="amazon.titan-embed-text-v2:0",
        description="Amazon Titan Test Embeddings Model ID",
    )
    BEDROCK_LLM_MODEL_ID: str = Field(
        default="amazon.nova-lite-v1:0", description="Amazon Nova Lite Model ID"
    )
    AWS_ACCESS_KEY_ID: str = Field(default="", description="AWS Access Key")
    AWS_SECRET_ACCESS_KEY: str = Field(default="", description="AWS Secret Key")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class TourAPIConfig(BaseSettings):
    TOUR_API_KEY: str = Field(default="", description="한국관광공사 Tour API 인증키")
    TOUR_API_BASE_URL: str = Field(
        default="https://apis.data.go.kr/B551011/KorService2",
        description="Tour API Base URL",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class KakaoMobilityConfig(BaseSettings):
    KAKAO_MOBILITY_API_KEY: str = Field(
        default="", description="Kakao Mobility REST API Key"
    )
    KAKAO_MOBILITY_DIRECTIONS_URL: str = Field(
        default="https://apis-navi.kakaomobility.com/v1/directions",
        description="Kakao Mobility Directions API URL",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class NestJSConfig(BaseSettings):
    # validation_alias : .env 파일의 변수명(NESTJS_SERVER_URL)을
    # 파이썬 변수명(NESTJS_BACKEND_URL)으로 매핑
    NESTJS_BACKEND_URL: str = Field(
        default="http://localhost:3000",
        validation_alias="NESTJS_SERVER_URL",
        description="NestJS Backend Base URL",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class RabbitMQConfig(BaseSettings):
    RABBITMQ_HOST: str = Field(default="localhost")
    RABBITMQ_PORT: int = Field(default=5672)
    RABBITMQ_USER: str = Field(default="guest")
    RABBITMQ_PASSWORD: str = Field(default="guest")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


openaiConfig = OpenAIConfig()
databaseConfig = DatabaseConfig()
naverSearchConfig = NaverSearchConfig()
embeddingConfig = EmbeddingConfig()
bedrockConfig = BedRockConfig()
tourAPIConfig = TourAPIConfig()
kakaoMobilityConfig = KakaoMobilityConfig()
nestJSConfig = NestJSConfig()
rabbitMQConfig = RabbitMQConfig()

if not nestJSConfig.NESTJS_BACKEND_URL:
    raise ValueError("오류: .env 파일에 NESTJS_SERVER_URL이 설정되지 않았습니다.")

if not bedrockConfig.AWS_ACCESS_KEY_ID or not bedrockConfig.AWS_SECRET_ACCESS_KEY:
    raise ValueError(
        "오류: .env 파일에 AWS 자격 증명(Access Key/Secret Key)이 없습니다."
    )
