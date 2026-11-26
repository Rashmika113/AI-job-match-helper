import pytest

from jobmatch.llm import PROVIDERS, get_llm


def test_groq_is_first_and_uses_a_current_model():
    assert list(PROVIDERS)[0] == "groq"
    assert PROVIDERS["groq"].default_model


def test_unknown_provider():
    with pytest.raises(ValueError):
        get_llm("nope")


def test_missing_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(ValueError, match="API key"):
        get_llm("groq")
