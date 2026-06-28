from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str | None = None
    human_review_threshold: float = 0.65
    max_spans_per_segment: int = 8

    # Retrieval (Perplexity-lite)
    enable_web_search: bool = True
    tavily_api_key: str = ""
    max_search_results: int = 3
    max_retrieved_pages: int = 5
    max_source_excerpt_chars: int = 2000


settings = Settings()
