from jobmatch.advisor import build_messages, stream_tips
from jobmatch.scorer import score_match


def test_prompt_contains_analysis(sample_cv, sample_job, fake_embedder):
    result = score_match(sample_cv, sample_job, fake_embedder)
    system, messages = build_messages(sample_cv, sample_job, result)
    user = messages[0]["content"]
    assert "Never invent experience" in system
    assert f"Overall score: {result.score}/100" in user
    for skill in result.missing_required:
        assert skill in user
    assert "Junior AI Engineer" in user and "Nimal Perera" in user


def test_sinhala_language_instruction(sample_cv, sample_job, fake_embedder):
    result = score_match(sample_cv, sample_job, fake_embedder)
    system, _ = build_messages(sample_cv, sample_job, result, language="සිංහල (Sinhala)")
    assert "Sinhala" in system


def test_stream_tips_uses_llm(sample_cv, sample_job, fake_embedder, fake_llm):
    result = score_match(sample_cv, sample_job, fake_embedder)
    text = "".join(stream_tips(fake_llm, sample_cv, sample_job, result))
    assert text.startswith("### Summary")
    assert len(fake_llm.calls) == 1
