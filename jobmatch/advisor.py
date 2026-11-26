"""Ask an LLM for concrete, honest CV tips, grounded in the computed match result."""

from __future__ import annotations

from collections.abc import Iterator

from .llm import LLM
from .scorer import MatchResult

LANGUAGES = {
    "English": "Write your answer in clear, simple English.",
    "සිංහල (Sinhala)": (
        "Write your answer in simple Sinhala (සිංහල). Keep technical terms, skill names and any "
        "CV text you suggest in English, because the CV itself is in English."
    ),
}

SYSTEM_PROMPT = """You are a friendly, practical career coach who helps people tailor their CV to a job post.

Rules:
- Base everything on the CV, the job post and the match analysis you are given.
- Never invent experience, degrees, employers or numbers. If a skill is missing, suggest an honest way
  to show it (a small project, a course, related experience already in the CV), not a fake claim.
- Be specific: quote or rewrite real lines from the CV. Avoid generic advice like "add more keywords".
- Keep it short and scannable with Markdown headings and bullets.
{language}"""

USER_TEMPLATE = """## Match analysis (computed by the app)
Overall score: {score}/100 ({label})
Skill overlap: {skill_score}
Semantic similarity: {semantic_score}
Required skills found in CV: {matched_required}
Required skills MISSING from CV: {missing_required}
Nice-to-have skills found: {matched_optional}
Nice-to-have skills missing: {missing_optional}
Job requirements the CV covers least:
{weakest}

## Job post
{job}

## CV
{cv}

Reply with exactly these sections:
### Summary
Two sentences: how well this CV fits and the single biggest gap.
### Top 5 CV edits
Numbered. For each: what to change, and a rewritten bullet the person can paste (only facts from the CV).
### Missing skills: what to do
For each important missing skill: is it a real gap or just not mentioned?
Give one honest, quick way to close it.
### Keywords to add
Comma-separated job-post terms the CV should mention, only where they are true for this person."""

MAX_CHARS = 12_000  # keeps prompts well inside small free-tier context windows


def _fmt(items: list[str]) -> str:
    return ", ".join(items) if items else "none"


def _pct(value: float | None) -> str:
    return "n/a (no known skills in the job post)" if value is None else f"{round(value * 100)}%"


def build_messages(cv_text: str, job_text: str, result: MatchResult, language: str = "English"):
    weakest = "\n".join(f"- ({round(c.score * 100)}%) {c.requirement}" for c in result.weakest_requirements)
    system = SYSTEM_PROMPT.format(language=LANGUAGES.get(language, LANGUAGES["English"]))
    user = USER_TEMPLATE.format(
        score=result.score,
        label=result.label,
        skill_score=_pct(result.skill_score),
        semantic_score=_pct(result.semantic_score),
        matched_required=_fmt(result.matched_required),
        missing_required=_fmt(result.missing_required),
        matched_optional=_fmt(result.matched_optional),
        missing_optional=_fmt(result.missing_optional),
        weakest=weakest or "- none",
        job=job_text[:MAX_CHARS],
        cv=cv_text[:MAX_CHARS],
    )
    return system, [{"role": "user", "content": user}]


def stream_tips(
    llm: LLM, cv_text: str, job_text: str, result: MatchResult, language: str = "English"
) -> Iterator[str]:
    system, messages = build_messages(cv_text, job_text, result, language)
    yield from llm.stream(system, messages)
