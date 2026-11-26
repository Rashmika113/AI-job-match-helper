"""Local, free text embeddings with sentence-transformers.

The default model, intfloat/multilingual-e5-small, covers 100 languages including
Sinhala and English, and matches across them: a Sinhala CV can be compared with an
English job post. It is ~470 MB and downloads once on first use.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Protocol


class Embedder(Protocol):
    # Raw cosine similarities differ per model; (low, high) maps them to a 0-1 score.
    calibration: tuple[float, float]

    def embed(self, texts: list[str]) -> list[list[float]]: ...


def calibration_for(model_name: str) -> tuple[float, float]:
    """Cosine range from "unrelated" to "very close" for a model family.

    E5 models squeeze almost everything into 0.7-1.0, so a raw 0.8 is only
    a medium match. Rescaling makes the semantic score readable as a percentage.
    """
    name = model_name.lower()
    if "e5" in name:
        return 0.75, 0.90
    return 0.20, 0.80  # typical for MiniLM / mpnet / bge style models


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str):
        self.model_name = model_name
        # E5 expects a short prefix; "query: " is right for symmetric comparisons like CV vs job.
        self.prefix = "query: " if "e5" in model_name.lower() else ""
        self.calibration = calibration_for(model_name)
        self._model = _load_model(model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(
            [self.prefix + t for t in texts], normalize_embeddings=True, show_progress_bar=False
        )
        return vectors.tolist()


@lru_cache(maxsize=2)
def _load_model(model_name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)
