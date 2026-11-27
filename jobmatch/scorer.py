"""The explainable match score.

final score = skill_weight    * skill overlap      (which job skills appear in the CV;
                                                     "FastAPI or Flask" counts as one skill)
            + semantic_weight * semantic similarity (how well each job requirement
                                                     is covered by some part of the CV)

Both parts are shown in the UI, together with the exact skills and requirement
lines behind them, so the user can see *why* they got the score.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from .embeddings import Embedder
from .skills import category_of, extract_job_skills, extract_skills

OPTIONAL_SKILL_WEIGHT = 0.5  # a nice-to-have skill counts half as much as a required one


@dataclass
class RequirementCoverage:
    requirement: str  # a line from the job post
    best_cv_match: str  # the CV passage closest to it
    score: float  # 0-1 after calibration


@dataclass
class MatchResult:
    score: int  # 0-100
    skill_score: float | None  # 0-1, None if the job post lists no known skills
    semantic_score: float  # 0-1
    matched_required: list[str] = field(default_factory=list)
    missing_required: list[str] = field(default_factory=list)  # "A or B" when either would do
    matched_optional: list[str] = field(default_factory=list)
    missing_optional: list[str] = field(default_factory=list)
    extra_cv_skills: list[str] = field(default_factory=list)  # in the CV, not asked for
    coverage: list[RequirementCoverage] = field(default_factory=list)

    @property
    def label(self) -> str:
        if self.score >= 75:
            return "Strong match"
        if self.score >= 50:
            return "Fair match"
        return "Weak match"

    @property
    def weakest_requirements(self) -> list[RequirementCoverage]:
        return sorted(self.coverage, key=lambda c: c.score)[:3]


_BULLET = re.compile(r"^\s*(?:[-*•●▪]|\d+[.)])\s*")


def _drop_title(job_text: str) -> list[str]:
    """The job post's lines, without a leading job title such as "AI Engineer - XYZ Tech".

    The first line is treated as a title only if the post is clearly structured (has
    bullets or "Heading:" lines further down), and that line is not a bullet or a
    sentence and is followed by a blank line or a heading.
    """
    lines = job_text.strip().splitlines()
    if len(lines) < 2:
        return lines
    first, second, rest = lines[0].strip(), lines[1].strip(), lines[1:]
    structured = any(_BULLET.match(line) or line.rstrip().endswith(":") for line in rest)
    is_title = (
        not _BULLET.match(first)
        and not first.endswith((".", "!", "?", ":"))
        and (not second or second.endswith(":"))
    )
    return rest if structured and is_title else lines


def split_requirements(job_text: str, min_words: int = 4) -> list[str]:
    """Job post lines that read like requirements (bullets, sentences), not titles or headers."""
    lines = []
    for raw in _drop_title(job_text):
        line = re.sub(r"^\s*[-*•●▪\d.)]+\s*", "", raw).strip()
        if len(line.split()) >= min_words and not line.endswith(":"):
            lines.append(line)
    return lines


def split_cv(cv_text: str, max_chars: int = 300) -> list[str]:
    """Cut the CV into small passages (roughly one bullet or a few short lines each)."""
    passages: list[str] = []
    current = ""
    for raw in cv_text.splitlines():
        line = raw.strip()
        if not line:
            if current:
                passages.append(current)
                current = ""
            continue
        if len(current) + len(line) + 1 > max_chars and current:
            passages.append(current)
            current = line
        else:
            current = f"{current} {line}".strip()
    if current:
        passages.append(current)
    return passages


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


def _calibrate(raw: float, low: float, high: float) -> float:
    return min(1.0, max(0.0, (raw - low) / (high - low)))


def semantic_coverage(cv_text: str, job_text: str, embedder: Embedder) -> list[RequirementCoverage]:
    requirements = split_requirements(job_text) or [job_text.strip()]
    passages = split_cv(cv_text) or [cv_text.strip()]
    vectors = embedder.embed(requirements + passages)
    req_vecs, cv_vecs = vectors[: len(requirements)], vectors[len(requirements) :]
    low, high = embedder.calibration

    coverage = []
    for req, rv in zip(requirements, req_vecs, strict=True):
        sims = [_cosine(rv, cv) for cv in cv_vecs]
        best = max(range(len(sims)), key=sims.__getitem__)
        coverage.append(RequirementCoverage(req, passages[best], _calibrate(sims[best], low, high)))
    return coverage


def score_match(
    cv_text: str,
    job_text: str,
    embedder: Embedder,
    skill_weight: float = 0.6,
    semantic_weight: float = 0.4,
) -> MatchResult:
    if not cv_text.strip() or not job_text.strip():
        raise ValueError("Both the CV and the job post need some text.")

    cv_skills = extract_skills(cv_text)
    job = extract_job_skills(job_text)

    def by_category(skills: set[str]) -> list[str]:
        return sorted(skills, key=lambda s: (category_of(s), s.lower()))

    def missing(units: list[frozenset[str]]) -> list[str]:
        gaps = [sorted(u, key=str.lower) for u in units if not u & cv_skills]
        gaps.sort(key=lambda g: (category_of(g[0]), g[0].lower()))
        return [" or ".join(g) for g in gaps]

    req_units, opt_units = job.units(job.required), job.units(job.optional)
    matched_req = sum(1 for u in req_units if u & cv_skills)
    matched_opt = sum(1 for u in opt_units if u & cv_skills)
    total = len(req_units) + OPTIONAL_SKILL_WEIGHT * len(opt_units)
    skill_score = (matched_req + OPTIONAL_SKILL_WEIGHT * matched_opt) / total if total else None

    coverage = semantic_coverage(cv_text, job_text, embedder)
    semantic = sum(c.score for c in coverage) / len(coverage)

    if skill_score is None:  # no known skills in the job post: rely on meaning only
        final = semantic
    else:
        final = (skill_weight * skill_score + semantic_weight * semantic) / (skill_weight + semantic_weight)

    return MatchResult(
        score=round(final * 100),
        skill_score=skill_score,
        semantic_score=semantic,
        matched_required=by_category(job.required & cv_skills),
        missing_required=missing(req_units),
        matched_optional=by_category(job.optional & cv_skills),
        missing_optional=missing(opt_units),
        extra_cv_skills=by_category(cv_skills - job.all),
        coverage=coverage,
    )
