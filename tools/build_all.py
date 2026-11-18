"""
Regenerates everything derived from the coded data, in order:
  classification master -> data/mapped_studies.csv -> class profile and Table V -> Section V examples (selection check, table) -> Figs. 1-8 -> CHECKLIST.md
then reports the body word count. Run from the project root:
    python tools/build_all.py
Afterwards compile:  pdflatex main && bibtex main && pdflatex main && pdflatex main
"""
import os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
steps = ["tools/build_mapped.py", "tools/class_profile.py", "tools/select_examples.py",
         "tables/make_examples_table.py", "tools/evaluation_profile.py", "tools/sensitivity.py",
         "figures/fig1_prisma.py", "figures/fig2_taxonomy.py", "figures/fig3_per_year.py",
         "figures/fig4_cooccurrence.py", "figures/fig5_type_metric.py",
         "figures/fig6_type_platform.py", "figures/fig7_static_dynamic.py", "figures/fig8_sets.py",
         "tools/check_submission.py", "tools/update_s3.py"]
for st in steps:
    cwd = os.path.join(ROOT, os.path.dirname(st))          # fig1/fig2 write next to themselves
    r = subprocess.run([sys.executable, os.path.basename(st)], cwd=cwd, capture_output=True, text=True)
    status = "ok" if r.returncode == 0 else "FAILED"
    print(f"{status:6s} {st}")
    if r.returncode:
        print(r.stderr); sys.exit(1)

s = open(os.path.join(ROOT, "main.tex"), encoding="utf-8").read()
body = s[s.index(r"\section{Introduction}"):s.index(r"\section*{Data and Code Availability}")]
body = re.sub(r"\\begin\{(table\*?|figure\*?|equation)\}.*?\\end\{\1\}", "", body, flags=re.S)
body = re.sub(r"\\input\{[^}]*\}|\\cite\{[^}]*\}|\\[a-zA-Z*]+|[{}$%]", " ", body)
print(f"Body text (Sections I-X, excluding tables, figures, equations): ~{len(body.split())} words")
