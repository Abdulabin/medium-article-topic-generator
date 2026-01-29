"""Configuration management for the Medium Topic Agent."""

import os
from typing import Literal
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # LLM Configuration (Model-Agnostic)
    llm_provider: Literal["ollama", "google-genai", "openai", "anthropic"] = Field(
        default="ollama",
        description="LLM provider to use"
    )
    llm_model: str = Field(
        default="gpt-oss:120b-cloud",
        description="Model name for the selected provider"
    )
    
    # Provider-specific API keys
    google_api_key: str | None = Field(default=None)
    openai_api_key: str | None = Field(default=None)
    anthropic_api_key: str | None = Field(default=None)
    ollama_api_key: str | None = Field(default=None)
    
    # Ollama Configuration
    ollama_base_url: str = Field(default="http://localhost:11434")
    
    # Agent Configuration
    max_topics: int = Field(default=10, ge=1, le=20)
    max_search_results: int = Field(default=10, ge=1, le=50)
    max_arxiv_results: int = Field(default=5, ge=1, le=20)
    
    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global settings instance
settings = Settings()


def get_llm_config() -> dict:
    """Get LLM configuration based on the selected provider."""
    config = {
        "model": f"{settings.llm_provider}:{settings.llm_model}",
    }
    
    if settings.llm_provider == "ollama":
        if settings.ollama_api_key:
            os.environ["OLLAMA_API_KEY"] = settings.ollama_api_key
    elif settings.llm_provider == "google-genai":
        if settings.google_api_key:
            os.environ["GOOGLE_API_KEY"] = settings.google_api_key
    elif settings.llm_provider == "openai":
        if settings.openai_api_key:
            os.environ["OPENAI_API_KEY"] = settings.openai_api_key
    elif settings.llm_provider == "anthropic":
        if settings.anthropic_api_key:
            os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key
    
    return config
