#app/parsers_core/experience_parser.py(main caller funtion:  extract_work_experience)
from typing import List, Dict, Tuple
import re

# import nlp from config if available
try:
    from ..config import nlp
except Exception:
    nlp = None

BULLET_RE = re.compile(r'^[\s\-\u2022\u2023\u25E6\*\•\▪\◦]+')
EXPERIENCE_HEADERS = ["work experience", "experience", "professional experience", "employment", "internship", "internships"]
SECTION_STOPS = ["education", "projects", "skills", "certifications"]

DATE_RANGE_RE = re.compile(
    r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s*\d{4}'
    r'(?:\s*[-–—to]+\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s*\d{4}|'
    r'\s*[-–—to]+\s*(?:Present|Current|Now))?)|\b(?:Present|Current|Now|\d{4})\b', re.I)


def _normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    for b in ["\u2022","•","◦","▪","\u2023","\u25E6"]:
        text = text.replace(b, " • ")
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text

def _find_section_lines(text: str, header_candidates=EXPERIENCE_HEADERS) -> List[str]:
    txt = _normalize(text)
    lines = [ln.rstrip() for ln in txt.splitlines()]
    header_idx = None
    lowered_lines = [re.sub(r'[^a-z0-9 ]',' ', ln.lower()) for ln in lines]
    for i, low in enumerate(lowered_lines):
        for cand in header_candidates:
            if cand in low.split():
                header_idx = i
                break
        if header_idx is not None:
            break
    if header_idx is None:
        # fallback: substring search
        for i, low in enumerate(lowered_lines):
            for cand in header_candidates:
                if cand in low:
                    header_idx = i
                    break
            if header_idx is not None:
                break
    if header_idx is None:
        return []
    out = []
    for ln in lines[header_idx+1:]:
        if not ln.strip():
            out.append("")
            continue
        low_ln = ln.lower()
        if any(re.search(rf'\b{re.escape(stop)}\b', low_ln) for stop in SECTION_STOPS):
            break
        out.append(ln)
    return out

def _is_role_company_line(s: str) -> bool:
    # common patterns: "Role at Company", "Role | Company", "Role, Company", "Role @ Company"
    if len(s.split()) > 20:
        return False
    return bool(re.search(r'\b(at|@|\||,)\b', s, re.I) and
                re.search(r'\b(Developer|Engineer|Manager|Intern|Analyst|Consultant|Freelancer|Associate|Lead|Head|Sr|Senior|Junior)\b', s, re.I))

def _extract_duration(block_lines: List[str]) -> str:
    joined = " ".join(block_lines)
    m = DATE_RANGE_RE.search(joined)
    if m:
        return m.group(0).strip()
    return ""

def extract_work_experience(text: str, debug: bool = False) -> Tuple[List[Dict[str,str]], List[Dict]]:
    lines = _find_section_lines(text)
    if not lines:
        return [], []

    experiences: List[Dict[str,str]] = []
    debug_groups: List[Dict] = []
    current = None  # {"role","company","lines":[], "bullets":[]}

    for i, ln in enumerate(lines + [""]):
        s = ln.strip()
        lookahead = lines[i+1:i+6] if i < len(lines) else []

        if not s:
            # blank: continue (used as separator)
            continue

        # skip tiny uppercase table labels
        if s.isupper() and len(s.split()) <= 6:
            continue

        # direct "Role at Company" lines
        if _is_role_company_line(s):
            # lookahead sanity: require bullets or date after this line (reduce false positives)
            if any(BULLET_RE.match(nl) for nl in lookahead) or any(DATE_RANGE_RE.search(nl) for nl in lookahead):
                if current:
                    debug_groups.append(current)
                    duration = _extract_duration(current.get("lines", []) + current.get("bullets", []))
                    experiences.append({
                        "company": current.get("company", "").strip(),
                        "position": current.get("role", "").strip(),
                        "duration": duration
                    })
                parts = re.split(r'\bat\b|\@|\||,', s, flags=re.I)
                role = parts[0].strip()
                company = parts[1].strip() if len(parts) > 1 else ""
                current = {"role": role, "company": company, "lines": [s], "bullets": []}
                continue
            else:
                # noisy single-line, treat conservatively (maybe a table row) -> skip
                continue

        # bracketed company e.g., "Freelancer (...) [Company]"
        br = re.search(r'\[(.*?)\]$', s)
        if br:
            company = br.group(1).strip()
            role = s[:br.start()].strip()
            if current:
                debug_groups.append(current)
                duration = _extract_duration(current.get("lines", []) + current.get("bullets", []))
                experiences.append({
                    "company": current.get("company", "").strip(),
                    "position": current.get("role", "").strip(),
                    "duration": duration
                })
            current = {"role": role, "company": company, "lines": [s], "bullets": []}
            continue

        # bullets -> buffer
        if BULLET_RE.match(s):
            if not current:
                # attempt to detect company ORG using nlp if available
                company_guess = ""
                if nlp:
                    try:
                        doc = nlp(s)
                        orgs = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
                        if orgs:
                            company_guess = orgs[0]
                    except Exception:
                        company_guess = ""
                current = {"role": "", "company": company_guess, "lines": [s], "bullets": []}
            current["bullets"].append(BULLET_RE.sub('', s).strip())
            continue

        # date line
        if DATE_RANGE_RE.search(s):
            if current:
                current.setdefault("meta", {})["date_line"] = s
            else:
                current = {"role": "", "company": "", "lines": [s], "bullets": [], "meta": {"date_line": s}}
            continue

        # NER company line + lookahead bullets -> treat as company header (use nlp if available)
        if nlp:
            try:
                doc = nlp(s)
                orgs = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
            except Exception:
                orgs = []
        else:
            orgs = []

        if orgs and any(BULLET_RE.match(nl) for nl in lookahead):
            if current:
                debug_groups.append(current)
                duration = _extract_duration(current.get("lines", []) + current.get("bullets", []))
                experiences.append({
                    "company": current.get("company", "").strip(),
                    "position": current.get("role", "").strip(),
                    "duration": duration
                })
            current = {"role": "", "company": orgs[0], "lines": [s], "bullets": []}
            continue

        # otherwise attach to current if present
        if current:
            current["lines"].append(s)
            # attach to last bullet if it's short else add new bullet
            if current["bullets"] and len(current["bullets"][-1].split()) < 10:
                current["bullets"][-1] = current["bullets"][-1] + " " + s
            else:
                current["bullets"].append(s)
            continue

        # stray: try to detect "Role, Company" pattern and start record only if looks plausible
        m = re.split(r'[,\-]\s*', s, maxsplit=1)
        if len(m) == 2 and re.search(r'\b(Developer|Engineer|Freelancer|Intern|Analyst|Manager|Consultant|Associate|Lead|Head)\b', m[0], re.I):
            role = m[0].strip()
            company = m[1].strip()
            current = {"role": role, "company": company, "lines": [s], "bullets": []}
            continue

        # else: ignore line conservatively
        continue

        # flush last
    if current:
        debug_groups.append(current)
        duration = _extract_duration(current.get("lines", []) + current.get("bullets", []))
        experiences.append({
            "company": current.get("company", "").strip(),
            "position": current.get("role", "").strip(),
            "duration": duration
        })

    if debug:
        return experiences, debug_groups
    return experiences, []

