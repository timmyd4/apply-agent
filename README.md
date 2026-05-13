# Apply Agent

Generates a tailored, ATS-optimized LaTeX resume for a job posting using Gemini AI, then compiles it to PDF via GitHub Actions.

---

## First-Time Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set your Gemini API key
Set `GEMINI_API_KEY` as a global Windows environment variable:

**Start → "Edit environment variables for your account" → New**
- Variable name: `GEMINI_API_KEY`
- Variable value: your key

Restart your terminal after adding it. The script reads it automatically — no config file needed.

### 3. Uncomment `output/*.tex` in `.gitignore`
GitHub Actions only builds PDFs when a `.tex` file is pushed to `output/`. By default this line is commented out — remove the `#` to enable it:
```
# Before:
#output/*.tex

# After:
output/*.tex
```

---

## Generating a Resume

### 1. Fill in `job_description.md`
At the top of the file, set the company and role in the YAML front matter:
```yaml
---
company: Google
role: Software Engineer Intern
---
```
Then paste the full job description text below the comment line.

### 2. Run the script
```bash
python generate_resume.py
```
This will:
- Generate a tailored `.tex` file in `output/`
- Add a new row to `applications.xlsx` with status **Generated**

### 3. Commit and push the `.tex` file
```bash
git add output/<filename>.tex
git commit -m "Add tailored resume for <Company>"
git push
```

### 4. Download the PDF
Go to your repo on GitHub → **Actions** → click the latest **"Build Resume PDFs"** run → scroll to the bottom → download the **`resume-pdfs`** artifact.

---

## Tracking Applications

Every time you run `generate_resume.py`, a row is added to `applications.xlsx` in the project root. Open it and update the **Status** column as things progress:

| Status | Color |
|--------|-------|
| Generated | White |
| Applied | Green |
| Interview | Yellow |
| Offer | Dark green |
| Rejected | Red |

`applications.xlsx` is gitignored — it stays local to your machine.

### Adding a resume that was already generated
If you need to manually log a resume that was already generated, run:
```bash
python -c "
from generate_resume import update_tracker
update_tracker('Company', 'Role_Name', 'Tim_Williams_Company_Role_timestamp.tex')
"
```

---

## Project Structure

```
Apply_Agent/
├── generate_resume.py         # Main script
├── instructions.md            # AI prompt instructions
├── job_description.md         # Paste job posting here before each run
├── Tim_Williams_Master_Resume.tex  # Full master resume
├── requirements.txt
├── applications.xlsx          # Local application tracker (gitignored)
├── skills/                    # YAML files describing each skill
│   ├── python.yaml
│   ├── java.yaml
│   └── ...
├── output/                    # Generated .tex files (committed to trigger CI)
└── .github/
    └── workflows/
        └── build.yml          # Compiles .tex → PDF artifact on push
```

---

## Notes

- PDFs are **never committed** to the repo — only available as GitHub Actions artifacts.
- The AI will never fabricate skills or experience; everything is grounded in the master resume and skill library.
- If a build fails with a LaTeX error, check the Actions log — the most common issue is a package or color name problem in the generated `.tex`.

---

## Using This Yourself (Forkers)

1. **Replace the master resume** — swap `Tim_Williams_Master_Resume.tex` with your own. Keep the same `\jobhead`, `\projhead`, `\skillrow` commands and preamble structure so the AI knows how to format the output.

2. **Update the skill library** — replace the `.yaml` files in `skills/` with your own. Each file should be named after the skill and describe your proficiency and relevant projects. The AI uses these to decide what to highlight.

3. **Update `instructions.md`** — replace Tim's name with yours anywhere it appears.

4. **Update `generate_resume.py`** — change the output filename prefix from `Tim_Williams_` to your own name (line that builds `out_file`).

5. **Set your Gemini API key** — as a global environment variable locally (see setup above) and as a GitHub Actions secret (`GEMINI_API_KEY`) in your forked repo's settings so the PDF build works.

6. **Uncomment `output/*.tex`** in `.gitignore` to enable the PDF build on push.
