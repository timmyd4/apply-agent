#!/usr/bin/env python3
import os
import re
import sys
import yaml
from google import genai
from google.genai import types
from pathlib import Path
from datetime import datetime
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, PatternFill, Alignment

ROOT = Path(__file__).parent
MASTER_RESUME = ROOT / "Tim_Williams_Master_Resume.tex"
SKILLS_DIR = ROOT / "skills"
JOB_DESCRIPTION = ROOT / "job_description.md"
INSTRUCTIONS = ROOT / "instructions.md"
OUTPUT_DIR = ROOT / "output"
TRACKER = ROOT / "applications.xlsx"

HEADERS = ["Date", "Company", "Role", "Resume File", "Status", "Notes"]
HEADER_FILL = PatternFill("solid", fgColor="1B3A5C")
HEADER_FONT = Font(bold=True, color="FFFFFF")
STATUS_COLORS = {
    "Generated": "FFFFFF",
    "Applied":   "D9EAD3",
    "Interview": "FFF2CC",
    "Offer":     "B6D7A8",
    "Rejected":  "F4CCCC",
}


def update_tracker(company: str, role: str, filename: str) -> None:
    if TRACKER.exists():
        wb = load_workbook(TRACKER)
        ws = wb.active
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = "Applications"
        for col, header in enumerate(HEADERS, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = HEADER_FONT
            cell.fill = HEADER_FILL
            cell.alignment = Alignment(horizontal="center")
        ws.column_dimensions["A"].width = 12
        ws.column_dimensions["B"].width = 22
        ws.column_dimensions["C"].width = 35
        ws.column_dimensions["D"].width = 55
        ws.column_dimensions["E"].width = 12
        ws.column_dimensions["F"].width = 30

    row = [
        datetime.now().strftime("%Y-%m-%d"),
        company.replace("_", " "),
        role.replace("_", " "),
        filename,
        "Generated",
        "",
    ]
    ws.append(row)

    last_row = ws.max_row
    fill = PatternFill("solid", fgColor=STATUS_COLORS["Generated"])
    for col in range(1, len(HEADERS) + 1):
        ws.cell(row=last_row, column=col).fill = fill

    wb.save(TRACKER)


def load_skills() -> str:
    skills = []
    for yaml_file in sorted(SKILLS_DIR.glob("*.yaml")):
        with open(yaml_file, encoding="utf-8") as f:
            skills.append(f"# {yaml_file.stem}\n{f.read()}")
    return "\n---\n".join(skills)


def extract_metadata(job_desc: str) -> tuple[str, str]:
    match = re.match(r"^---\n(.*?)\n---", job_desc, re.DOTALL)
    if match:
        try:
            meta = yaml.safe_load(match.group(1))
            if meta:
                company = re.sub(r"[^\w\-]", "_", str(meta.get("company", "Company")).strip())
                role = re.sub(r"[^\w\-]", "_", str(meta.get("role", "Role")).strip())
                return company, role
        except Exception:
            pass
    return "Company", "Role"


COVER_LETTER_INSTRUCTION = (
    "You are writing a short, genuine cover letter paragraph for Tim Williams, a software engineering student. "
    "Write in first person as Tim. The paragraph should sound like a real person — warm, direct, and enthusiastic — not corporate or stiff. "
    "Convey that Tim is a hard worker who puts in the effort to get things done right, that he genuinely wants to grow as a software engineer and soak up as much as he can, "
    "and that he's excited about this specific company and role. Reference something concrete from the job description to show it's not a generic letter. "
    "Keep it to 3–4 sentences. Do not use buzzwords like 'synergy', 'impactful', 'leverage', 'passionate about technology', or 'drive business value'. "
    "Sound like a motivated student who means it, not a LinkedIn post. "
    "Return only the paragraph text — no salutation, no closing, no subject line, no extra formatting."
)

COVER_LETTER_TEMPLATE = r"""\documentclass[12pt]{{article}}
\usepackage[margin=1in]{{geometry}}
\usepackage{{times}}
\usepackage{{parskip}}
\pagestyle{{empty}}

\begin{{document}}

\textbf{{Tim Williams}} \hfill timmywilliams4665@gmail.com

\vspace{{1em}}

{date}

\vspace{{1em}}

Hiring Manager \\
{company}

\vspace{{1em}}

Dear Hiring Manager,

{paragraph}

\vspace{{1em}}

Sincerely,

\vspace{{2em}}

Tim Williams

\end{{document}}
"""


def generate_cover_letter(client, company: str, role: str, job_description: str, timestamp: str) -> Path:
    prompt = (
        f"Company: {company.replace('_', ' ')}\n"
        f"Role: {role.replace('_', ' ')}\n\n"
        f"Job Description:\n{job_description}"
    )

    print(f"Generating cover letter for {company} — {role}...")

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=COVER_LETTER_INSTRUCTION,
            max_output_tokens=8192,
        ),
        contents=prompt,
    )

    paragraph = response.text.strip()

    tex = COVER_LETTER_TEMPLATE.format(
        date=datetime.now().strftime("%B %d, %Y"),
        company=company.replace("_", " "),
        paragraph=paragraph,
    )

    out_file = OUTPUT_DIR / f"Tim_Williams_{company}_{role}_CoverLetter_{timestamp}.tex"
    out_file.write_text(tex, encoding="utf-8")
    return out_file


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable is not set.")
        sys.exit(1)

    for path in [MASTER_RESUME, JOB_DESCRIPTION, INSTRUCTIONS]:
        if not path.exists():
            print(f"ERROR: Missing required file: {path}")
            sys.exit(1)

    master_resume = MASTER_RESUME.read_text(encoding="utf-8")
    job_description = JOB_DESCRIPTION.read_text(encoding="utf-8").strip()
    instructions = INSTRUCTIONS.read_text(encoding="utf-8")
    skills_yaml = load_skills()

    if not job_description or job_description.endswith("-->"):
        print("ERROR: job_description.md appears empty — paste the job posting below the comment.")
        sys.exit(1)

    company, role = extract_metadata(job_description)

    client = genai.Client(api_key=api_key)

    prompt = (
        f"## Master Resume\n```latex\n{master_resume}\n```\n\n"
        f"## Skill Library\n```yaml\n{skills_yaml}\n```\n\n"
        f"## Job Description\n\n{job_description}"
    )

    print(f"Generating resume for {company} — {role}...")

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=instructions,
            max_output_tokens=16384,
        ),
        contents=prompt,
    )

    tailored_tex = response.text.strip()

    # Strip markdown fences if the model wrapped the output anyway
    if tailored_tex.startswith("```"):
        lines = tailored_tex.splitlines()
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        tailored_tex = "\n".join(lines[1:end])

    if not tailored_tex.endswith(r"\end{document}"):
        print("WARNING: Resume output appears truncated — \\end{document} not found. Check the .tex file before committing.")

    OUTPUT_DIR.mkdir(exist_ok=True)
    for old in OUTPUT_DIR.glob("*.tex"):
        old.unlink()

    timestamp = datetime.now().strftime("%Y-%m-%d")
    out_file = OUTPUT_DIR / f"Tim_Williams_{company}_{role}_{timestamp}.tex"
    out_file.write_text(tailored_tex, encoding="utf-8")
    update_tracker(company, role, out_file.name)

    cover_letter_file = generate_cover_letter(client, company, role, job_description, timestamp)

    print(f"Saved:  {out_file}")
    print(f"Saved:  {cover_letter_file}")
    print(f"Tracker updated: {TRACKER}")


if __name__ == "__main__":
    main()
