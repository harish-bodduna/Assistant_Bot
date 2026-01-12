from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized configuration loaded from environment variables or .env."""

    azure_tenant_id: str = Field(..., alias="AZURE_TENANT_ID")
    azure_client_id: str = Field(..., alias="AZURE_CLIENT_ID")
    azure_client_secret: str = Field(..., alias="AZURE_CLIENT_SECRET")

    sharepoint_site_id: str = Field(..., alias="SHAREPOINT_SITE_ID")
    sharepoint_drive_id: Optional[str] = Field(None, alias="SHAREPOINT_DRIVE_ID")
    sharepoint_folder_path: Optional[str] = Field(None, alias="SHAREPOINT_FOLDER_PATH")

    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    openai_api_base: Optional[str] = Field(None, alias="OPENAI_API_BASE")

    qdrant_url: str = Field(..., alias="QDRANT_URL")
    qdrant_api_key: Optional[str] = Field(None, alias="QDRANT_API_KEY")
    qdrant_collection_visual: str = Field("tech_manuals", alias="QDRANT_COLLECTION_VISUAL")
    qdrant_collection_text: str = Field("tech_manuals_text_only", alias="QDRANT_COLLECTION_TEXT")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()  # type: ignore[arg-type]

