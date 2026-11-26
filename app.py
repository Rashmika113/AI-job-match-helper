"""Streamlit UI: add a CV and a job post, get an explainable match score and CV tips.

Run with:  streamlit run app.py
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from jobmatch.advisor import LANGUAGES, stream_tips
from jobmatch.config import settings
from jobmatch.llm import PROVIDERS, get_llm
from jobmatch.loader import clean_text, read_upload
from jobmatch.scorer import MatchResult, score_match

SAMPLES = Path(__file__).parent / "samples"

st.set_page_config(page_title="AI Job-Match Helper", page_icon="🎯", layout="wide")


@st.cache_resource(show_spinner="Loading embedding model (first run downloads ~470 MB)...")
def get_embedder():
    from jobmatch.embeddings import SentenceTransformerEmbedder

    return SentenceTransformerEmbedder(settings.embedding_model)


def load_sample(job_file: str) -> None:
    st.session_state.cv_text = (SAMPLES / "sample_cv.txt").read_text(encoding="utf-8")
    st.session_state.job_text = (SAMPLES / job_file).read_text(encoding="utf-8")
    st.session_state.pop("result", None)
    st.session_state.pop("tips", None)


# ---- Sidebar: model settings ---------------------------------------------
with st.sidebar:
    st.header("⚙️ Model")
    provider_keys = list(PROVIDERS)
    provider = st.selectbox(
        "LLM provider (for CV tips)",
        provider_keys,
        index=provider_keys.index(settings.default_provider) if settings.default_provider in PROVIDERS else 0,
        format_func=lambda k: PROVIDERS[k].label,
    )
    info = PROVIDERS[provider]
    model = st.text_input("Model", value=info.default_model)
    api_key = None
    if info.needs_api_key:
        api_key = st.text_input(
            f"API key ({info.api_key_env})", type="password", help="Leave empty to use the .env value."
        )
    if provider == "ollama":
        st.caption(f"Make sure Ollama is running and you've pulled the model: `ollama pull {model}`")
    language = st.radio("Tips language", list(LANGUAGES), horizontal=True)

    st.header("🧪 Try it")
    st.button("Load sample (English job)", on_click=load_sample, args=("sample_job.txt",))
    st.button("Load sample (Sinhala job)", on_click=load_sample, args=("sample_job_si.txt",))
    st.caption(
        "The score is computed locally and is free. Only the **CV tips** step calls the LLM, "
        "which sends your CV and the job post to the provider you choose."
    )

# ---- Inputs ---------------------------------------------------------------
st.title("🎯 AI Job-Match Helper")
st.caption(
    "Compare your CV with a job post: get a match score you can understand, the skills you have "
    "and miss, and concrete tips to improve your CV. Works with English and Sinhala (සිංහල)."
)

left, right = st.columns(2)
with left:
    st.subheader("1. Your CV")
    upload = st.file_uploader("Upload a PDF or .txt", type=["pdf", "txt", "md"])
    if upload is not None and st.session_state.get("uploaded_id") != (upload.name, upload.size):
        try:
            st.session_state.cv_text = read_upload(upload.name, upload.getvalue())
            st.session_state.uploaded_id = (upload.name, upload.size)
        except ValueError as exc:
            st.error(str(exc))
    cv_text = st.text_area("...or paste it here", key="cv_text", height=320)
with right:
    st.subheader("2. The job post")
    job_text = st.text_area("Paste the job description", key="job_text", height=405)

if st.button("🔍 Check match", type="primary", use_container_width=True):
    try:
        with st.spinner("Scoring..."):
            st.session_state.result = score_match(
                clean_text(cv_text),
                clean_text(job_text),
                get_embedder(),
                skill_weight=settings.skill_weight,
                semantic_weight=settings.semantic_weight,
            )
        st.session_state.pop("tips", None)
    except ValueError as exc:
        st.warning(str(exc))


# ---- Results ----------------------------------------------------------------
def chips(skills: list[str], color: str) -> str:
    return " ".join(f":{color}-background[{s}]" for s in skills) if skills else "_none_"


def show_result(r: MatchResult) -> None:
    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("Match score", f"{r.score}/100", r.label, delta_color="off")
    c2.metric("Skill overlap", "n/a" if r.skill_score is None else f"{round(r.skill_score * 100)}%")
    c3.metric("Semantic similarity", f"{round(r.semantic_score * 100)}%")
    st.progress(r.score / 100)
    st.caption(
        f"Score = {settings.skill_weight:.0%} skill overlap + {settings.semantic_weight:.0%} semantic "
        "similarity. Skill overlap counts the job's skills found in your CV (nice-to-haves count half). "
        "Semantic similarity checks how well each job requirement is covered by some part of your CV."
    )

    a, b = st.columns(2)
    with a:
        st.markdown("**✅ Required skills you have**")
        st.markdown(chips(r.matched_required, "green"))
        st.markdown("**➕ Nice-to-haves you have**")
        st.markdown(chips(r.matched_optional, "blue"))
    with b:
        st.markdown("**❌ Required skills missing**")
        st.markdown(chips(r.missing_required, "red"))
        st.markdown("**◻️ Nice-to-haves missing**")
        st.markdown(chips(r.missing_optional, "orange"))
    if r.extra_cv_skills:
        with st.expander("Other skills in your CV (not asked for in this job)"):
            st.markdown(chips(r.extra_cv_skills, "gray"))

    with st.expander("How well each job requirement is covered"):
        for c in sorted(r.coverage, key=lambda c: c.score):
            st.markdown(f"**{round(c.score * 100)}%** · {c.requirement}")
            st.caption(f"Closest part of your CV: {c.best_cv_match[:250]}")


if result := st.session_state.get("result"):
    show_result(result)

    st.subheader("3. CV tips")
    if st.button("✨ Get CV tips from AI"):
        try:
            llm = get_llm(provider, model=model, api_key=api_key)
            st.session_state.tips = st.write_stream(
                stream_tips(llm, clean_text(cv_text), clean_text(job_text), result, language)
            )
        except Exception as exc:  # show provider errors instead of crashing
            st.error(f"⚠️ {type(exc).__name__}: {exc}")
    elif tips := st.session_state.get("tips"):
        st.markdown(tips)
