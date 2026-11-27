import pytest

from jobmatch.scorer import score_match, split_cv, split_requirements


def test_split_requirements_skips_headers_and_strips_bullets(sample_job):
    reqs = split_requirements(sample_job)
    assert "Requirements:" not in reqs
    assert any(r.startswith("Strong Python skills") for r in reqs)
    assert all(not r.startswith("-") for r in reqs)


@pytest.mark.parametrize("gap", ["\n\n", "\n"])
def test_split_requirements_skips_job_title(gap):
    job = f"Junior AI Engineer - XYZ Tech (Colombo){gap}Requirements:\n- Strong Python and SQL skills"
    assert split_requirements(job) == ["Strong Python and SQL skills"]


def test_split_requirements_skips_sinhala_job_title():
    job = "කනිෂ්ඨ දත්ත විශ්ලේෂක (Junior Data Analyst) - කොළඹ\n\nඅවශ්‍යතා:\n- Excel පිළිබඳ හොඳ දැනුමක්"
    assert split_requirements(job) == ["Excel පිළිබඳ හොඳ දැනුමක්"]


@pytest.mark.parametrize(
    "first_line",
    [
        "- Strong Python and SQL skills",  # a bullet
        "We need strong Python and SQL skills.",  # a sentence
    ],
)
def test_split_requirements_keeps_first_line_that_is_not_a_title(first_line):
    job = f"{first_line}\n\nNice to have:\n- Some experience with Docker"
    assert len(split_requirements(job)) == 2


def test_split_requirements_keeps_first_line_of_unstructured_post():
    job = "Strong Python and SQL skills\n\nSome experience with Docker"
    assert len(split_requirements(job)) == 2


def test_split_cv_keeps_passages_short():
    text = "\n".join(["word " * 20] * 10)
    assert all(len(p) <= 300 for p in split_cv(text))


def test_sample_match_is_explainable(sample_cv, sample_job, fake_embedder):
    r = score_match(sample_cv, sample_job, fake_embedder)
    assert 0 <= r.score <= 100
    assert {"Python", "Git", "Testing"} <= set(r.matched_required)
    assert "FastAPI or Flask" in r.missing_required
    assert "Docker" in r.missing_optional
    assert r.coverage and all(0 <= c.score <= 1 for c in r.coverage)
    assert len(r.weakest_requirements) == 3


def test_perfect_skills_beat_no_skills(fake_embedder):
    job = "Requirements:\n- Python and SQL experience required for data work"
    good = score_match("Python and SQL experience in data work", job, fake_embedder)
    bad = score_match("Professional chef with ten years in kitchens", job, fake_embedder)
    assert good.skill_score == 1.0
    assert bad.skill_score == 0.0
    assert good.score > bad.score


def test_optional_skills_count_half(fake_embedder):
    job = "Requirements:\n- Python\nNice to have:\n- Docker"
    r = score_match("Python developer", job, fake_embedder, skill_weight=1.0, semantic_weight=0.0)
    assert r.skill_score == pytest.approx(1 / 1.5)


def test_job_without_known_skills_uses_semantic_only(fake_embedder):
    r = score_match(
        "I love baking bread every morning", "Looking for someone who loves baking bread", fake_embedder
    )
    assert r.skill_score is None
    assert r.score == round(r.semantic_score * 100)


def test_empty_input_raises(fake_embedder):
    with pytest.raises(ValueError):
        score_match("", "job", fake_embedder)


def test_one_of_an_or_group_is_enough(fake_embedder):
    job = "Requirements:\n- Python\n- FastAPI or Flask"
    flask = score_match("Python and Flask", job, fake_embedder, skill_weight=1.0, semantic_weight=0.0)
    neither = score_match("Python only", job, fake_embedder, skill_weight=1.0, semantic_weight=0.0)
    assert flask.skill_score == 1.0
    assert flask.missing_required == []
    assert neither.skill_score == 0.5
    assert neither.missing_required == ["FastAPI or Flask"]
