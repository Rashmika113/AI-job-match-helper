"""Central configuration, read from environment variables (or a .env file)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _env_float(name: str, default: float) -> float:
    return float(os.getenv(name, default))


@dataclass(frozen=True)
class Settings:
    # Embeddings run locally on CPU, so scoring is free and private.
    # Multilingual so Sinhala and English CVs / job posts both work.
    embedding_model: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-small")
    )

    # Final score = skill_weight * skill overlap + semantic_weight * semantic similarity
    skill_weight: float = field(default_factory=lambda: _env_float("SKILL_WEIGHT", 0.6))
    semantic_weight: float = field(default_factory=lambda: _env_float("SEMANTIC_WEIGHT", 0.4))

    # Default LLM provider shown in the UI.
    default_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "groq"))


settings = Settings()
