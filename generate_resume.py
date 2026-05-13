#!/usr/bin/env python3
import os
import re
import sys
import yaml
import anthropic
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent
MASTER_RESUME = ROOT / "Tim_Williams_Master_Resume.tex"
SKILLS_DIR = ROOT / "skills"
JOB_DESCRIPTION = ROOT / "job_description.md"
INSTRUCTIONS = ROOT / "instructions.md"
OUTPUT_DIR = ROOT / "output"


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


def main():
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

    client = anthropic.Anthropic()

    static_content = (
        f"## Master Resume\n```latex\n{master_resume}\n```\n\n"
        f"## Skill Library\n```yaml\n{skills_yaml}\n```"
    )

    print(f"Generating resume for {company} — {role}...")

    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=8192,
        system=[
            {
                "type": "text",
                "text": instructions,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": static_content,
                        "cache_control": {"type": "ephemeral"},
                    },
                    {
                        "type": "text",
                        "text": f"## Job Description\n\n{job_description}",
                    },
                ],
            }
        ],
    )

    tailored_tex = response.content[0].text.strip()

    # Strip markdown fences if the model wrapped the output anyway
    if tailored_tex.startswith("```"):
        lines = tailored_tex.splitlines()
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        tailored_tex = "\n".join(lines[1:end])

    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = OUTPUT_DIR / f"Tim_Williams_{company}_{role}_{timestamp}.tex"
    out_file.write_text(tailored_tex, encoding="utf-8")

    print(f"Saved:  {out_file}")

    usage = response.usage
    parts = [f"input: {usage.input_tokens}", f"output: {usage.output_tokens}"]
    if getattr(usage, "cache_read_input_tokens", 0):
        parts.append(f"cache read: {usage.cache_read_input_tokens}")
    if getattr(usage, "cache_creation_input_tokens", 0):
        parts.append(f"cache write: {usage.cache_creation_input_tokens}")
    print(f"Tokens — {', '.join(parts)}")


if __name__ == "__main__":
    main()
