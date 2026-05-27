import json
import time
import google.generativeai as genai
import asyncio
from typing import Dict, Any
from .config import GOOGLE_API_KEY


# Check if the API key was loaded
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found. Please set it in your .env file.")

# Configure the Gemini client with your API key
genai.configure(api_key=GOOGLE_API_KEY)


model = genai.GenerativeModel('gemini-pro-latest')

# helper: lenient JSON extractor (handles prose around JSON)
def _extract_json_block(text: str) -> str:
    """Return the first balanced {...} JSON object found in text, or '' if none."""
    if not text:
        return ""
    start = text.find('{')
    if start == -1:
        return ""
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i+1]
    return ""

def generate_summary_and_sections(resume_text: str, max_retries: int = 2) -> Dict[str, Any]:
    """
    Single LLM call that returns:
      {
        "summary": "<3-4 sentence summary string>",
        "projects": [ { "title": "...", "tech": [...], "bullets":[...], "start_end": "" }, ... ],
        "experience": [ { "company":"", "position":"", "duration":"", "bullets":[...] }, ... ]
      }

    The function enforces valid JSON output and normalizes missing fields to empty lists/strings.
    """
    prompt = f"""
You are an expert resume analyst. Read the resume text below and extract:

1. **Professional Summary** — Write a short, direct, and professional summary (3–4 sentences) describing the candidate's background, experience, and skills.  
   - Write it like a human recruiter would.  
   - DO NOT start with phrases like "Yes, of course", "Based on the resume", "This candidate", or "The person".  
   - Begin immediately with the main point about the candidate
   - Keep it formal and concise.

2. **Projects** — A list of the candidate's key projects.  
   Each project object should have:
   - "title": string  
   - "tech": array of technologies  
   - "bullets": array of 1–3 concise description points  
   - "start_end": optional date or duration string  

3. **Experience** — A list of professional experiences or internships.  
   Each object should include:
   - "company": string  
   - "position": string  
   - "duration": string (if present)  
   - "bullets": array of 1–3 concise points describing work done  

Return ONLY one JSON object (no markdown, no text outside it) with top-level keys:
{{
  "summary": string,
  "projects": [ ... ],
  "experience": [ ... ]
}}

If a field is missing, use empty string or [].
Resume text:
\"\"\"\n{resume_text}\n\"\"\"
"""

    for attempt in range(max_retries + 1):
        try:
            resp = model.generate_content(prompt)
            raw = resp.text.strip()
            jtxt = _extract_json_block(raw)
            if not jtxt:
                raise ValueError("no json found")
            parsed = json.loads(jtxt)
            if not isinstance(parsed, dict):
                raise ValueError("json not an object")
            # light-safe extraction
            summary = str(parsed.get("summary", "")).strip() if parsed.get("summary") else ""
            projects = parsed.get("projects", [])
            experience = parsed.get("experience", [])
            # ensure types
            if not isinstance(projects, list):
                projects = []
            if not isinstance(experience, list):
                experience = []
            return {"summary": summary, "projects": projects, "experience": experience}
        except Exception as e:
            print(f"[generate_summary_and_sections] attempt {attempt} error: {e}")
            if attempt < max_retries:
                time.sleep(0.4 + attempt * 0.4)
                continue
            return {"summary": "", "projects": [], "experience": []}

async def perform_skill_gap_analysis(candidate_skills: list, job_description: str) -> dict:
    """
    Uses the Gemini API to perform a skill-gap analysis.
    """
    prompt = f"""
Act as an expert technical recruiter. Your task is to perform a skill-gap analysis.

Candidate Skills: {candidate_skills}
Job Description:
---
{job_description}
---

Perform the analysis and return ONLY a JSON object with the following keys:
- "required_skills": A list of all key skills required by the job description.
- "candidate_has_skills": A list of skills from the candidate's list that match the required skills.
- "missing_skills": A list of required skills that the candidate does not have.
- "candidate_score": An integer (from 0 to 100) representing how well the candidate's skills match the job description. 100 is a perfect match.
"""

    try:
        response = await model.generate_content_async(prompt)
        raw_text = response.text.strip()
        # Use the JSON extractor to safely find the JSON block
        json_text = _extract_json_block(raw_text)
        if not json_text:
            raise ValueError("No JSON found in Gemini response")
        return json.loads(json_text)
    except Exception as e:
        print(f"[perform_skill_gap_analysis] error: {e}")
        return {"error": "Could not perform skill-gap analysis."}
