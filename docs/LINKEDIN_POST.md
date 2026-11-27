# LinkedIn post draft

Replace the bracketed parts, attach the demo GIF (LinkedIn autoplays GIFs and video better than links), and put the repo link in the first comment if you want more reach.

---

Ever wondered why a CV gets rejected before a human even reads it? 🤔 I built an AI Job-Match Helper to find out. 🎯

You paste your CV and a job post, and it tells you:
✅ a match score from 0 to 100
✅ which skills you have and which you're missing
✅ which job requirements your CV covers least
✅ concrete tips to improve the CV, with rewritten bullet points

The part I cared most about: the score is explainable, not just "the AI says 72".

🔹 Skill overlap (60%): I wrote a skill extractor that knows aliases (sklearn = scikit-learn), tells "Java" apart from "JavaScript", treats "Nice to have" skills as half weight, and counts "FastAPI or Flask" as one skill
🔹 Semantic similarity (40%): every job requirement is compared with every part of the CV using a local multilingual embedding model, so "built a chatbot over PDFs" still counts toward "experience with RAG"
🔹 Only then does an LLM write the tips, using those numbers, with strict instructions never to invent experience

It works with Sinhala (සිංහල) job posts too, and can write the tips in Sinhala. 🇱🇰

What I learned:
• Explainable beats impressive. Seeing *why* the score is low is what makes it useful.
• Embedding similarity scores need calibrating. Raw cosine values all sit between 0.7 and 0.9, so I rescale them.
• Small details matter in skill matching: "R", "Go" and "REST" are also normal English words!
• [Add one thing you noticed when testing it on your own CV.]

The score runs free on your laptop; tips use Groq's free tier by default (or Ollama, OpenAI, Claude). Built with Python, FastAPI, a hand-made HTML/CSS/JS frontend, sentence-transformers and pytest, with CI on GitHub Actions.

This is project 2 in my AI portfolio. Project 1 was a Sinhala + English "Chat with your PDFs" RAG app.

Code: [GitHub link]

#AI #MachineLearning #LLM #NLP #Python #CareerTips #GenerativeAI #SriLanka #OpenToWork
