import re
from .config import nlp
from .ai_enhancer import generate_summary_and_sections
from .parsers_core.name_parser import extract_name
from .parsers_core.skills_parser import extract_skills
from .parsers_core.education_parser import extract_education
from .parsers_core.experience_parser import extract_work_experience
from .parsers_core.projects_parser import extract_projects

def parse_resume_text(text: str) -> dict:
    doc = nlp(text)
    parsed_data = {"name": extract_name(text, doc), "email": "Not Found"}

    # Email extraction
    email_pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
    emails = re.findall(email_pattern, text)
    if emails:
        parsed_data["email"] = emails[0]

    # Skills
    parsed_data["skills"] = extract_skills(text)

    # Education
    parsed_data["education"] = extract_education(text)

    # Work Experience
    parsed_data["work_experience"] = extract_work_experience(text)

    # Projects
    parsed_data["projects"] = extract_projects(text)

    # LLM extraction (one call) for summary + projects + experience
    llm_result = generate_summary_and_sections(text)

    # Merge: prefer existing deterministic fields if present, but add/overwrite summary/projects/experience
    parsed_data["summary"] = llm_result.get("summary", "")
    parsed_data["projects"] = llm_result.get("projects", [])
    parsed_data["work_experience"] = llm_result.get("experience", [])

    return parsed_data
