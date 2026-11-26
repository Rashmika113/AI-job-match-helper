"""Find skills in free text with a small, editable skill dictionary.

Each canonical skill has a list of aliases. Matching is case-insensitive and
respects word boundaries, so "Java" is not found inside "JavaScript" and
"C++" / "C#" / "Node.js" still match. Non-ASCII aliases (Sinhala) are matched
as plain substrings, because Sinhala vowel signs are not "word" characters.

Add your own skills to SKILLS: that is the easiest way to improve the scorer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache

# canonical name -> (category, aliases). The canonical name itself is always an alias.
SKILLS: dict[str, tuple[str, list[str]]] = {
    # Programming languages
    "Python": ("Languages", []),
    "Java": ("Languages", []),
    "JavaScript": ("Languages", ["js", "es6"]),
    "TypeScript": ("Languages", []),
    "C++": ("Languages", ["cpp"]),
    "C#": ("Languages", ["csharp", "c sharp"]),
    "Go": ("Languages", ["golang"]),
    "Rust": ("Languages", []),
    "Kotlin": ("Languages", []),
    "Swift": ("Languages", []),
    "PHP": ("Languages", []),
    "R": ("Languages", ["r programming", "rstudio"]),
    "SQL": ("Languages", ["t-sql", "pl/sql"]),
    "Bash": ("Languages", ["shell scripting", "shell script"]),
    # Data & AI
    "Machine Learning": ("Data & AI", ["ml", "machine-learning"]),
    "Deep Learning": ("Data & AI", ["neural networks", "neural network"]),
    "NLP": ("Data & AI", ["natural language processing"]),
    "Computer Vision": ("Data & AI", ["opencv"]),
    "LLMs": ("Data & AI", ["llm", "large language models", "large language model", "generative ai", "genai"]),
    "RAG": ("Data & AI", ["retrieval-augmented generation", "retrieval augmented generation"]),
    "Prompt Engineering": ("Data & AI", []),
    "LangChain": ("Data & AI", []),
    "PyTorch": ("Data & AI", ["torch"]),
    "TensorFlow": ("Data & AI", ["keras"]),
    "scikit-learn": ("Data & AI", ["sklearn", "scikit learn"]),
    "Hugging Face": ("Data & AI", ["huggingface", "transformers"]),
    "Pandas": ("Data & AI", []),
    "NumPy": ("Data & AI", []),
    "Data Analysis": ("Data & AI", ["data analytics", "data analyst"]),
    "Data Visualization": ("Data & AI", ["data visualisation", "matplotlib", "seaborn", "plotly"]),
    "Statistics": ("Data & AI", ["statistical"]),
    "Power BI": ("Data & AI", ["powerbi"]),
    "Tableau": ("Data & AI", []),
    "Excel": ("Data & AI", ["ms excel", "microsoft excel"]),
    "Vector Databases": ("Data & AI", ["vector database", "chromadb", "chroma", "pinecone", "faiss"]),
    # Web & apps
    "HTML": ("Web & Apps", ["html5"]),
    "CSS": ("Web & Apps", ["css3", "tailwind", "bootstrap"]),
    "React": ("Web & Apps", ["react.js", "reactjs"]),
    "Angular": ("Web & Apps", []),
    "Vue": ("Web & Apps", ["vue.js", "vuejs"]),
    "Node.js": ("Web & Apps", ["nodejs", "node"]),
    "Django": ("Web & Apps", []),
    "Flask": ("Web & Apps", []),
    "FastAPI": ("Web & Apps", []),
    "Streamlit": ("Web & Apps", []),
    "Spring Boot": ("Web & Apps", ["spring framework"]),
    "REST APIs": ("Web & Apps", ["rest api", "restful", "api development"]),
    "GraphQL": ("Web & Apps", []),
    "Flutter": ("Web & Apps", []),
    "Android": ("Web & Apps", []),
    # Cloud & DevOps
    "AWS": ("Cloud & DevOps", ["amazon web services"]),
    "Azure": ("Cloud & DevOps", ["microsoft azure"]),
    "GCP": ("Cloud & DevOps", ["google cloud"]),
    "Docker": ("Cloud & DevOps", ["containers", "containerization"]),
    "Kubernetes": ("Cloud & DevOps", ["k8s"]),
    "CI/CD": ("Cloud & DevOps", ["ci / cd", "continuous integration", "github actions", "jenkins"]),
    "Git": ("Cloud & DevOps", ["github", "gitlab", "version control"]),
    "Linux": ("Cloud & DevOps", ["ubuntu", "unix"]),
    "Testing": ("Cloud & DevOps", ["unit testing", "pytest", "unit tests", "test automation", "tdd"]),
    # Databases
    "PostgreSQL": ("Databases", ["postgres"]),
    "MySQL": ("Databases", []),
    "MongoDB": ("Databases", ["mongo"]),
    "Redis": ("Databases", []),
    "Firebase": ("Databases", []),
    # Ways of working
    "Agile": ("Ways of Working", ["scrum", "kanban", "jira"]),
    "Communication": ("Soft Skills", ["communication skills", "සන්නිවේදන"]),
    "Teamwork": ("Soft Skills", ["team player", "collaboration", "කණ්ඩායම්"]),
    "Leadership": ("Soft Skills", ["team lead", "mentoring", "නායකත්ව"]),
    "Problem Solving": ("Soft Skills", ["problem-solving", "analytical skills", "ගැටලු විසඳීම"]),
    "English": ("Languages Spoken", ["english language", "ඉංග්‍රීසි"]),
    "Sinhala": ("Languages Spoken", ["සිංහල"]),
}

# Words that tell us a line in a job post is "nice to have", not a hard requirement.
_OPTIONAL_HINTS = re.compile(
    r"nice[ -]to[ -]have|preferred|is a plus|are a plus|bonus|desirable|an advantage|added advantage"
    r"|optional|good to have|වාසියකි|වාසිදායක"
)
_REQUIRED_HEADER = re.compile(
    r"requirement|required|must|qualification|responsibilit|what you.?ll do|skills|අවශ්‍යතා"
)


@dataclass(frozen=True)
class SkillHit:
    name: str
    category: str


@dataclass
class JobSkills:
    required: set[str] = field(default_factory=set)
    optional: set[str] = field(default_factory=set)
    # Alternatives written as "FastAPI or Flask": having any one of them is enough.
    groups: list[frozenset[str]] = field(default_factory=list)

    @property
    def all(self) -> set[str]:
        return self.required | self.optional

    def units(self, skills: set[str]) -> list[frozenset[str]]:
        """Group `skills` into scoring units: one per "A or B" group, one per remaining skill."""
        units: list[frozenset[str]] = []
        for group in self.groups:
            unit = group & skills
            if len(unit) >= 2 and unit not in units:
                units.append(unit)
        grouped = set().union(*units) if units else set()
        units += [frozenset({s}) for s in sorted(skills - grouped)]
        return units


@lru_cache(maxsize=1)
def _patterns() -> list[tuple[str, re.Pattern[str]]]:
    compiled = []
    for name, (_, aliases) in SKILLS.items():
        for alias in {name.lower(), *(a.lower() for a in aliases)}:
            if alias.isascii():
                # Not preceded/followed by a letter, digit or one of + # . (so "c++" and "node.js" work).
                pattern = rf"(?<![\w+#]){re.escape(alias)}(?![\w+#]|\.\w)"
            else:
                pattern = re.escape(alias)
            compiled.append((name, re.compile(pattern)))
    return compiled


def category_of(skill: str) -> str:
    return SKILLS[skill][0] if skill in SKILLS else "Other"


def extract_skills(text: str) -> set[str]:
    """Return the canonical names of all skills mentioned in `text`."""
    lowered = text.lower()
    found = set()
    for name, pattern in _patterns():
        if name in found:
            continue
        if name == "R" and not _looks_like_r_language(text):
            continue
        if pattern.search(lowered):
            found.add(name)
    # A lone "Go" is too common an English word; only trust it with a tech-looking capital G.
    if "Go" in found and not re.search(r"(?<!\w)(Go|golang|Golang)(?!\w)", text):
        found.discard("Go")
    return found


def _looks_like_r_language(text: str) -> bool:
    # Only accept a bare "R" when it is capitalised and listed like a skill (e.g. "Python, R, SQL").
    return bool(re.search(r"(?:^|[,/(|•\-]\s*)R(?:\s*[,/)|]|\s*$)", text, re.MULTILINE)) or bool(
        re.search(r"r programming|rstudio", text.lower())
    )


def extract_job_skills(job_text: str) -> JobSkills:
    """Split a job post's skills into required and nice-to-have, using section headers and hints."""
    result = JobSkills()
    optional_section = False
    for line in job_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        lowered = stripped.lower()
        is_header = len(stripped) < 60 and (stripped.endswith(":") or stripped.startswith("#"))
        if is_header:
            if _OPTIONAL_HINTS.search(lowered):
                optional_section = True
            elif _REQUIRED_HEADER.search(lowered):
                optional_section = False
        skills = extract_skills(stripped)
        result.groups += _or_groups(stripped)
        if optional_section or _OPTIONAL_HINTS.search(lowered):
            result.optional |= skills
        else:
            result.required |= skills
    # If a skill shows up as required anywhere, it counts as required.
    result.optional -= result.required
    return result


_SEGMENT_SPLIT = re.compile(r"[,;()\[\]]| and | සහ ")
_OR_WORD = re.compile(r" or | හෝ | / ", re.IGNORECASE)


def _or_groups(line: str) -> list[frozenset[str]]:
    """Find alternatives such as "(FastAPI or Flask)" or "Power BI හෝ Tableau" in one line."""
    groups = []
    for segment in _SEGMENT_SPLIT.split(line):
        if _OR_WORD.search(segment):
            skills = extract_skills(segment)
            if len(skills) >= 2:
                groups.append(frozenset(skills))
    return groups
