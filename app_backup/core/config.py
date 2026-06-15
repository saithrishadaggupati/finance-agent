import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from functools import lru_cache

load_dotenv(override=True)

os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")
os.environ["LANGCHAIN_PROJECT"] = "finance-agent"


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # App
    app_name: str = "Finance Agent"
    app_version: str = "1.0.0"
    debug: bool = True

    # Groq
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"

    # Memory
    memory_db_path: str = "data/memory.db"
    max_memory_items: int = 50


def get_settings() -> Settings:
    return Settings()