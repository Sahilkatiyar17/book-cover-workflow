from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Typed, validated access to environment variables.
    Nothing else in the app should call os.environ directly —
    always go through Settings.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "book-cover-workflow"
    langsmith_endpoint: str = "https://api.smith.langchain.com"

    # LLM providers
    groq_api_key: str
    groq_api_key_1 : str
    groq_model: str = "llama-3.3-70b-versatile"
    nvidia_api_key: str = ""
    gemini_api_key: str = ""
    cohere_api_key: str = ""

    # Image search providers
    unsplash_api_key: str = ""
    pexels_api_key: str = ""
    serpapi_api_key: str = ""
    apify_api_key: str = ""
    pixabay_api_key: str = ""

    # App
    app_env: str = "dev"
    mem0_api_key: str = ""
    
        # LLM providers
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"
    nvidia_api_key: str = ""
    gemini_api_key: str = ""
    cohere_api_key: str = ""
    openai_api_key: str = ""
   
    huggingface_api_key: str = ""

@lru_cache
def get_settings() -> Settings:
    """Cached singleton — import this function, never instantiate Settings() directly elsewhere."""
    return Settings()