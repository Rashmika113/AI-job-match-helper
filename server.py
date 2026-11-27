"""FastAPI backend: a small JSON API plus the static web frontend in ./web.

Run with:  python run.py        (opens the browser for you)
     or:   uvicorn server:app --reload
"""

from __future__ import annotations

from dataclasses import asdict
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from jobmatch.advisor import LANGUAGES, stream_tips
from jobmatch.config import settings
from jobmatch.embeddings import Embedder
from jobmatch.llm import PROVIDERS, get_llm
from jobmatch.loader import clean_text, read_upload
from jobmatch.scorer import MatchResult, score_match

ROOT = Path(__file__).parent
WEB = ROOT / "web"
SAMPLES = {"cv": "sample_cv.txt", "job": "sample_job.txt", "job_si": "sample_job_si.txt"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

app = FastAPI(title="AI Job-Match Helper")


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    """Loaded once, on the first match (the first run downloads the model)."""
    from jobmatch.embeddings import SentenceTransformerEmbedder

    return SentenceTransformerEmbedder(settings.embedding_model)


EmbedderDep = Annotated[Embedder, Depends(get_embedder)]


class MatchRequest(BaseModel):
    cv_text: str = Field(max_length=60_000)
    job_text: str = Field(max_length=30_000)


class TipsRequest(MatchRequest):
    provider: str = settings.default_provider
    model: str | None = None
    api_key: str | None = None
    language: str = "English"


def _result_json(result: MatchResult) -> dict:
    data = asdict(result)
    data["label"] = result.label
    data["weakest_requirements"] = [asdict(c) for c in result.weakest_requirements]
    return data


def _score(req: MatchRequest, embedder: Embedder) -> MatchResult:
    try:
        return score_match(
            clean_text(req.cv_text),
            clean_text(req.job_text),
            embedder,
            skill_weight=settings.skill_weight,
            semantic_weight=settings.semantic_weight,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/config")
def config() -> dict:
    return {
        "default_provider": settings.default_provider,
        "providers": [
            {
                "key": p.key,
                "label": p.label,
                "default_model": p.default_model,
                "needs_api_key": p.needs_api_key,
            }
            for p in PROVIDERS.values()
        ],
        "languages": list(LANGUAGES),
        "skill_weight": settings.skill_weight,
        "semantic_weight": settings.semantic_weight,
    }


@app.get("/api/samples/{name}")
def sample(name: str) -> dict:
    if name not in SAMPLES:
        raise HTTPException(status_code=404, detail="Unknown sample")
    return {"text": (ROOT / "samples" / SAMPLES[name]).read_text(encoding="utf-8")}


@app.post("/api/extract")
async def extract(file: Annotated[UploadFile, File()]) -> dict:
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File is larger than 10 MB.")
    try:
        return {"text": read_upload(file.filename or "", data)}
    except Exception as exc:  # bad or encrypted PDFs raise various errors
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/match")
def match(req: MatchRequest, embedder: EmbedderDep) -> dict:
    return _result_json(_score(req, embedder))


@app.post("/api/tips")
def tips(req: TipsRequest, embedder: EmbedderDep) -> StreamingResponse:
    result = _score(req, embedder)
    try:
        llm = get_llm(req.provider, model=req.model or None, api_key=req.api_key or None)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    def generate():
        try:
            yield from stream_tips(
                llm, clean_text(req.cv_text), clean_text(req.job_text), result, req.language
            )
        except Exception as exc:  # show provider errors (bad key, retired model...) in the page
            yield f"\n\n⚠️ **{type(exc).__name__}:** {exc}"

    return StreamingResponse(generate(), media_type="text/plain; charset=utf-8")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB / "index.html")


app.mount("/static", StaticFiles(directory=WEB), name="static")
