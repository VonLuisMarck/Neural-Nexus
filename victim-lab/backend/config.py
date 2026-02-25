import os
from dataclasses import dataclass


@dataclass
class Settings:
    ollama_host: str
    ollama_model: str
    lab_id: str
    jwt_secret_key: str


def get_settings() -> Settings:
    return Settings(
        ollama_host=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
        ollama_model=os.environ.get("OLLAMA_MODEL", "llama3"),
        lab_id=os.environ.get("LAB_ID", "ai-lab"),
        jwt_secret_key=os.environ.get("JWT_SECRET_KEY", "change-me"),
    )
