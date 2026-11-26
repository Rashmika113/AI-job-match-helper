"""Shared fixtures. Tests use a tiny fake embedder so they run offline in seconds."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

import pytest

SAMPLES = Path(__file__).parent.parent / "samples"


class FakeEmbedder:
    """Bag-of-words hashed into a fixed-size vector: crude, but similar texts score higher."""

    dim = 256
    calibration = (0.0, 1.0)  # raw cosine is already 0-1 for non-negative vectors

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for word in (w.strip(".,?!:;()[]-") for w in text.lower().split()):
            if word:
                vec[int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed(self, texts):
        return [self._embed(t) for t in texts]


class FakeLLM:
    name = "fake"

    def __init__(self):
        self.calls = []

    def stream(self, system, messages):
        self.calls.append((system, messages))
        yield "### Summary\n"
        yield "Good fit."


@pytest.fixture
def fake_embedder():
    return FakeEmbedder()


@pytest.fixture
def fake_llm():
    return FakeLLM()


@pytest.fixture
def sample_cv():
    return (SAMPLES / "sample_cv.txt").read_text(encoding="utf-8")


@pytest.fixture
def sample_job():
    return (SAMPLES / "sample_job.txt").read_text(encoding="utf-8")


@pytest.fixture
def sample_job_si():
    return (SAMPLES / "sample_job_si.txt").read_text(encoding="utf-8")
