import os
from dataclasses import dataclass


@dataclass
class Settings:
    ollama_host: str
    ollama_model: str
    lab_id: str
    jwt_secret_key: str
    c2_url: str


def get_settings() -> Settings:
    return Settings(
        ollama_host=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
        ollama_model=os.environ.get("OLLAMA_MODEL", "llama3"),
        lab_id=os.environ.get("LAB_ID", "ai-lab"),
        jwt_secret_key=os.environ.get("JWT_SECRET_KEY", "change-me"),
        # NN_C2: C2 server reachable from inside the victim container.
        # In Docker: host.docker.internal resolves to the host via extra_hosts.
        # Override with NN_C2=http://<real-ip>:5001 when running without Docker.
        c2_url=os.environ.get("NN_C2", "http://host.docker.internal:5001"),
    )
