from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = Field(default='SSBG Gateway', alias='APP_NAME')
    app_env: str = Field(default='development', alias='APP_ENV')
    app_debug: bool = Field(default=True, alias='APP_DEBUG')
    api_v1_prefix: str = Field(default='/api/v1', alias='API_V1_PREFIX')
    host: str = Field(default='0.0.0.0', alias='HOST')
    port: int = Field(default=8000, alias='PORT')

    database_url: str = Field(
        default='postgresql+asyncpg://ssbg:ssbg@localhost:5432/ssbg',
        alias='DATABASE_URL',
    )
    database_url_sync: str = Field(
        default='postgresql+psycopg://ssbg:ssbg@localhost:5432/ssbg',
        alias='DATABASE_URL_SYNC',
    )

    minio_endpoint: str = Field(default='http://localhost:9000', alias='MINIO_ENDPOINT')
    minio_bucket: str = Field(default='ssbg-backups', alias='MINIO_BUCKET')
    key_store_path: str = Field(default='./keys', alias='KEY_STORE_PATH')
    api_key_header: str = Field(default='X-API-Key', alias='API_KEY_HEADER')
    mfa_header: str = Field(default='X-MFA-Token', alias='MFA_HEADER')


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
