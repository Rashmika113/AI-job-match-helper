# 🎯 AI Job-Match Helper

Paste or upload your CV and a job post, and get:

- a **match score (0-100) you can actually understand**, not just an LLM's guess
- the **skills you have and the ones you're missing** (required vs nice-to-have)
- **which job requirements your CV covers least**
- **concrete, honest CV tips** from an LLM: rewritten bullets, how to close each gap, keywords to add

Works with **English and Sinhala (සිංහල)** job posts and CVs, and can write the tips in either language.

![Demo](assets/demo.gif)

![CI](https://github.com/Rashmika113/AI-job-match-helper/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

- **Explainable score** = 60% skill overlap + 40% semantic similarity (weights are configurable)
- **Skill extraction** from a dictionary of ~70 tech and soft skills with aliases (`sklearn` → scikit-learn, `k8s` → Kubernetes), careful word boundaries (`Java` is not found inside `JavaScript`, `C++` still matches), and Sinhala aliases (සන්නිවේදන → Communication)
- **Understands job post structure**: skills under "Nice to have:" or lines saying "is a plus" count half, and "FastAPI or Flask" counts as one skill you can satisfy either way
- **Requirement coverage**: each job requirement is compared with every part of your CV using a local multilingual embedding model, so you see exactly which requirement is weakest and the closest line in your CV
- **The score is free and private**: it is computed on your laptop. Only the optional "CV tips" step calls an LLM
- **Swap the LLM under AI settings**: Groq (free tier, default), Ollama (local), OpenAI or Anthropic Claude
- **Honest tips**: the prompt forbids inventing experience and asks for rewritten bullets using only facts from your CV
- **Colorful web UI** (plain HTML, CSS and JavaScript, no build step) on top of a **FastAPI** backend, with drag-and-drop CV upload, an animated score ring and AI tips that stream in live
- Tested with **pytest** (offline, under a second) and linted with **ruff** in GitHub Actions

## How the score works

```mermaid
flowchart LR
    CV[CV: PDF / text] --> SK1[Extract skills]
    JOB[Job post] --> SK2[Extract skills<br/>required / nice-to-have / A-or-B]
    SK1 --> OV[Skill overlap %]
    SK2 --> OV
    CV --> P[Split CV into passages]
    JOB --> R[Split job into requirement lines]
    P --> E[Embed locally<br/>multilingual-e5-small]
    R --> E
    E --> COV[Best CV passage per requirement<br/>= semantic similarity %]
    OV --> S[Score = 0.6 x skills + 0.4 x semantic]
    COV --> S
    S --> LLM[LLM tips<br/>Groq / Ollama / OpenAI / Claude]
```

1. **Skill overlap**: the job's skills are found and split into *required* and *nice-to-have*. Score = required skills found + half of nice-to-haves found, divided by the total possible.
2. **Semantic similarity**: every requirement line ("Hands-on experience with LLMs and RAG") is embedded and compared with every passage of your CV. The best match per requirement is rescaled to 0-100%, then averaged. This catches experience described in different words ("built a chatbot over PDFs" vs "RAG").
3. **Final score**: a weighted mix of the two. Both parts, and the exact skills and lines behind them, are shown in the app.
4. **Tips**: the LLM gets the CV, the job post and this analysis, so its advice is grounded in real numbers instead of guessing.

## Project structure

```
├── server.py            # FastAPI backend: JSON API + serves the web page
├── run.py               # python run.py -> starts the server and opens your browser
├── web/                 # colorful frontend: index.html, style.css, app.js (no npm needed)
├── jobmatch/
│   ├── loader.py        # PDF / text -> clean text
│   ├── skills.py        # skill dictionary + extraction (required / optional / A-or-B)
│   ├── embeddings.py    # local sentence-transformers wrapper
│   ├── scorer.py        # the explainable match score
│   ├── advisor.py       # prompt + streamed CV tips (English / Sinhala)
│   ├── llm.py           # one streaming interface over 4 providers
│   └── config.py        # settings from .env
├── samples/             # sample CV + English and Sinhala job posts
└── tests/               # offline tests with a fake embedder and LLM
```

## Getting started (Windows)

Requires Python 3.10+. In **cmd**:

```bat
cd "D:\Personal_Projects\AI job-match helper"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Open `.env` in Notepad and paste your free Groq key after `GROQ_API_KEY=` (get one at [console.groq.com/keys](https://console.groq.com/keys)). Then:

```bat
python run.py
```

Your browser opens http://127.0.0.1:8000 automatically. Click **Use sample CV** and **English sample** (or **සිංහල sample**), then **Check match**. Press `Ctrl+C` in cmd to stop the server.

For development, `uvicorn server:app --reload` restarts the server whenever you save a file. The API docs are at http://127.0.0.1:8000/docs.

The first "Check match" downloads the embedding model (about 470 MB), so it takes a few minutes once. After that it's fast.

> macOS / Linux: use `source .venv/bin/activate` and `cp .env.example .env`.

### Other LLMs

- **Ollama (local, free)**: install from [ollama.com](https://ollama.com/download), run `ollama pull llama3.2`, pick Ollama under **AI settings**. Small local models are weak at Sinhala.
- **OpenAI / Claude (paid)**: set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in `.env`, or paste the key under **AI settings** on the page.
- Groq retires models from time to time. If you get a "model not found" error, pick a current model in the [Groq playground](https://console.groq.com/playground) and set `GROQ_MODEL` in `.env` (or type it under **AI settings**).

## Configuration

| Variable | Default | What it does |
|---|---|---|
| `LLM_PROVIDER` | `groq` | Provider selected when the app opens |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Model for each provider (`OLLAMA_MODEL`, `OPENAI_MODEL`, `ANTHROPIC_MODEL` too) |
| `EMBEDDING_MODEL` | `intfloat/multilingual-e5-small` | Any sentence-transformers model. `multilingual-e5-base` is better but 1.1 GB |
| `SKILL_WEIGHT` / `SEMANTIC_WEIGHT` | `0.6` / `0.4` | How much each part counts in the final score |

To teach the app new skills, add them to `SKILLS` in [`jobmatch/skills.py`](jobmatch/skills.py).

## Running tests

```bat
pip install -r requirements-dev.txt
pytest
ruff check .
```

## Privacy

The score runs fully on your computer. When you click **Get CV tips**, your CV and the job post are sent to the LLM provider you picked (or stay local with Ollama). Use the sample CV for demos if you'd rather not send your own.

## Limitations and ideas for next steps

- Skill extraction is dictionary-based: precise and explainable, but it only knows skills in the list. An LLM-based extractor could be added as a fallback.
- The semantic part is calibrated for E5 models; other embedding models may need a different range in `calibration_for()`.
- Scanned PDF CVs have no text layer. OCR (e.g. Tesseract with the `sin` model) would fix that.
- Ideas: compare one CV against several jobs and rank them, export the tips as a PDF, deploy to Render or Hugging Face Spaces.

## License

[MIT](LICENSE)
