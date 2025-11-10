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


class KakaoLocalConfig(BaseSettings):
    KAKAO_REST_API_KEY: str = Field(default="", description="Kakao REST API Key")
    KAKAO_LOCAL_API_URL: str = Field(
        default="https://dapi.kakao.com/v2/local/search/category.json"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class BedRockConfig(BaseSettings):
    AWS_REGION: str = Field(default="")
    MODEL_ID: str = Field(default="")
    AWS_ACCESS_KEY_ID: str = Field(default="")
    AWS_SECRET_ACCESS_KEY: str = Field(default="")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


openaiConfig = OpenAIConfig()
databaseConfig = DatabaseConfig()
naverSearchConfig = NaverSearchConfig()
embeddingConfig = EmbeddingConfig()
kakaoLocalConfig = KakaoLocalConfig()
bedrockConfig = BedRockConfig()
