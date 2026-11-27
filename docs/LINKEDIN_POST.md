# LinkedIn post

Attach `demo-video/ai-job-match-helper-demo-1080p.mp4` and paste the text below the line.

---

Does your CV actually match the job you're applying for? 🤔 I built an AI Job-Match Helper to check. 🎯

Paste your CV and a job post, and it shows you:
✅ a match score from 0 to 100
✅ which skills you have and which you're missing
✅ which job requirements your CV covers least
✅ concrete CV tips, with rewritten bullet points

The part I cared most about: the score is explainable, not just "the AI says 72".

🔹 Skill overlap (60%): a skill extractor that knows aliases (sklearn = scikit-learn), tells "Java" apart from "JavaScript", counts "Nice to have" skills as half, and treats "FastAPI or Flask" as one skill
🔹 Semantic similarity (40%): a local multilingual embedding model compares every job requirement with every part of the CV
🔹 Only then does an LLM write the tips, using those results, with instructions never to invent experience

It works with Sinhala (සිංහල) job posts too, and can write the tips in Sinhala. 🇱🇰

What I learned:
• Seeing why a score is low is more useful than the number itself.
• Raw embedding similarity scores sit close together, so they need rescaling.
• Skill matching is full of traps: "R", "Go" and "REST" are also normal English words!

The score is computed on your laptop. Tips use Groq's free tier by default (Ollama, OpenAI and Claude also work). Built with Python, FastAPI, HTML/CSS/JavaScript, sentence-transformers and pytest, with CI on GitHub Actions.

This is project 2 in my AI portfolio. Project 1 was a Sinhala + English "Chat with your PDFs" RAG app.

Code: https://github.com/Rashmika113/AI-job-match-helper

#AI #MachineLearning #LLM #NLP #Python #GenerativeAI #SriLanka #OpenToWork
