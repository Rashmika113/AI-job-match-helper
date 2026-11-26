from jobmatch.skills import extract_job_skills, extract_skills


def test_finds_canonical_names_and_aliases():
    found = extract_skills("Built APIs with fastapi, used sklearn and k8s, deployed on Amazon Web Services.")
    assert {"FastAPI", "scikit-learn", "Kubernetes", "AWS"} <= found


def test_word_boundaries():
    found = extract_skills("Frontend work in JavaScript and Node.js")
    assert "JavaScript" in found
    assert "Node.js" in found
    assert "Java" not in found


def test_symbols_in_skill_names():
    found = extract_skills("Languages: C++, C#, Python")
    assert {"C++", "C#", "Python"} <= found


def test_common_words_are_not_skills():
    found = extract_skills("Ready to go the extra mile. R&D for the rest of the year in spring.")
    assert "Go" not in found
    assert "R" not in found


def test_r_language_in_a_skill_list():
    assert "R" in extract_skills("Skills: Python, R, SQL")


def test_sinhala_aliases():
    found = extract_skills("හොඳ සන්නිවේදන කුසලතා සහ කණ්ඩායම් හැඟීම")
    assert {"Communication", "Teamwork"} <= found


def test_job_skills_split_required_and_optional(sample_job):
    job = extract_job_skills(sample_job)
    assert {"Python", "LLMs", "RAG", "Git", "Testing"} <= job.required
    assert {"Docker", "AWS", "LangChain", "React"} <= job.optional
    assert not job.required & job.optional


def test_inline_optional_hint():
    job = extract_job_skills("Requirements:\n- Python and SQL\n- Docker is a plus")
    assert job.required == {"Python", "SQL"}
    assert job.optional == {"Docker"}


def test_sinhala_job_post_sections(sample_job_si):
    job = extract_job_skills(sample_job_si)
    assert {"Python", "SQL", "Pandas", "Excel", "Communication"} <= job.required
    assert {"Statistics", "AWS"} <= job.optional


def test_or_alternatives_become_a_group(sample_job, sample_job_si):
    assert frozenset({"FastAPI", "Flask"}) in extract_job_skills(sample_job).groups
    assert any({"Power BI", "Tableau"} <= g for g in extract_job_skills(sample_job_si).groups)
