#!/usr/bin/env python3
"""
make_screening_batches.py -- split records_for_screening.csv into Excel workbooks
for title-and-abstract screening, one set of identical workbooks per reviewer,
so that two reviewers can screen independently (each opens only their own files).

Each workbook holds up to --size records, with drop-down lists for the decision
(Include / Maybe / Exclude) and the exclusion reason (EC1-EC6), a Criteria sheet
and a Summary sheet that counts the decisions in that file.

Order: records whose title, abstract or keywords contain all three search blocks
(hybrid term, planning term, platform term) come first, so the most likely
relevant records are screened first; within each group, newest first.

The same 100 random pilot records (seed 2026) are also written to pilot_<TAG>.xlsx.

USAGE
  python make_screening_batches.py --records merged/records_for_screening.csv \
      --out screening/reviewer_ZA --reviewer "Zubaidah B. Alalwani" --tag ZA --size 2000
"""
import argparse, math, os

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

CRITERIA = [
    ("IC1", "Combines at least two method families (F1 graph search, F2 sampling, F3 reactive, F4 optimization, "
            "F5 metaheuristic, F6 learning/AI), each performing an identifiable planning function at run time."),
    ("IC2", "Targets a mobile robot (wheeled, tracked, or legged), an autonomous road vehicle, or an aerial, surface, "
            "or underwater vehicle. Manipulators and robot arms are out of scope (EC3)."),
    ("IC3", "Reports a quantitative evaluation in simulation or physical experiments using at least one planning "
            "metric (path length, time, success rate, smoothness, clearance, energy, collisions, ...)."),
    ("IC4", "Peer-reviewed journal article or full conference paper, in English, published 1 Jan 2015 to 31 Dec 2025."),
    ("EC1", "Single-family variant, intra-family combination (two methods of the same family, e.g. GA + PSO), or "
            "offline hyperparameter tuning of a single planner by another method."),
    ("EC2", "No quantitative evaluation (conceptual or purely theoretical work)."),
    ("EC3", "Out of scope: motion planning of a manipulator or robot arm (fixed or mounted on a mobile base), "
            "tracking control without a planning component, perception or SLAM only, task allocation without path planning, or non-robotic routing "
            "(network routing, vehicle routing problems)."),
    ("EC4", "Insufficient methodological detail to identify the components and how they are integrated."),
    ("EC5", "Duplicate or superseded version (a conference paper later extended into a journal article: keep the "
            "journal version unless the conference paper reports distinct experiments)."),
    ("EC6", "Not peer reviewed (preprints, theses, patents), not in English, abstract only, or retracted."),
]

# Scope rules agreed on 11 Oct 2026 (protocol v1.1), written into the Rules sheet of the pilot files
SCOPE_RULES = [
    ("Motion planning of a manipulator or robot arm, fixed or on a mobile base", "Exclude, EC3 (use EC3 even if single-family)", ""),
    ("Navigation of the mobile base of a mobile manipulator (the arm is not planned)", "Judge as a mobile robot", ""),
]

F = Font(name="Arial", size=10)
FB = Font(name="Arial", size=10, bold=True)
FT = Font(name="Arial", size=12, bold=True)
FH = Font(name="Arial", size=10, bold=True, color="FFFFFFFF")
HF = PatternFill("solid", fgColor="FF1F4E79")
YF = PatternFill("solid", fgColor="FFFFF2CC")
THIN = Side(style="thin", color="FFBFBFBF")
COLS = ["No", "Record ID", "Title", "Year", "Venue", "Abstract", "Keywords", "Found by", "Search terms found",
        "Decision", "Reason (EC)", "Note"]
WIDTHS = [6, 9, 42, 6, 22, 85, 30, 16, 10, 12, 10, 36]


def build(batch, k, n_batches, path, first_no, reviewer, tag, pilot=False):
    wb = Workbook()
    ws = wb.active
    ws.title = "Instructions"
    title = (f"Pilot screening ({len(batch)} records)" if pilot
             else f"Title and abstract screening, batch {k} of {n_batches} ({len(batch):,} records)")
    lines = [
        (f"{title}: reviewer {reviewer} ({tag})", FT),
        ("Two reviewers screen the same records independently. Fill only the yellow columns of the Screening sheet, "
         "do not change the other columns or the Record IDs, and do not look at the other reviewer's files.", F),
        ("", F),
        ("How to decide", FB),
        ("Include: the record probably meets all of IC1-IC4 (Criteria sheet).", F),
        ("Maybe: it might meet them, but the title and abstract do not say enough. Maybe goes to full-text assessment, like Include.", F),
        ("Exclude: it clearly fails at least one criterion. Give the first criterion that applies, in the order EC1 to EC6.", F),
        ("When in doubt, choose Maybe. Apply the rules agreed after the pilot (Rules sheet of the pilot file).", F),
        ("", F),
        ("Tips", FB),
        ("Use the filter arrows in the header row; 'Search terms found' shows which of C1 (hybrid), C2 (planning) and C3 (platform) "
         "appear in the record. Records with all three come first.", F),
        ("Save often, keeping the file name. When both reviewers have finished, tools/screening_reconcile.py merges the two sets, "
         "computes Cohen's kappa and lists the disagreements for discussion.", F),
    ]
    for i, (t, f) in enumerate(lines, 1):
        c = ws.cell(row=i, column=1, value=t)
        c.font = f
        c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["A"].width = 120

    sc = wb.create_sheet("Screening", 1)
    sc.append(COLS)
    for i, (_, r) in enumerate(batch.iterrows()):
        sc.append([first_no + i, r["record_id"], r["title"], int(r["year"]) if r["year"] else None, r["venue"],
                   r["abstract"], r["keywords"][:400], r["sources"], r["blocks_found"], None, None, None])
    for c in sc[1]:
        c.font = FH
        c.fill = HF
        c.alignment = Alignment(wrap_text=True, vertical="center")
    last = len(batch) + 1
    for row in sc.iter_rows(min_row=2, max_row=last):
        for c in row:
            c.font = F
            c.alignment = Alignment(wrap_text=True, vertical="top")
            c.border = Border(bottom=THIN)
        for j in (9, 10, 11):
            row[j].fill = YF
    for col, w in zip("ABCDEFGHIJKL", WIDTHS):
        sc.column_dimensions[col].width = w
    sc.freeze_panes = "D2"
    sc.auto_filter.ref = f"A1:L{last}"
    dv = DataValidation(type="list", formula1='"Include,Maybe,Exclude"', allow_blank=True)
    dv.error, dv.errorTitle = "Choose Include, Maybe or Exclude", "Decision"
    sc.add_data_validation(dv)
    dv.add(f"J2:J{last}")
    dv2 = DataValidation(type="list", formula1='"EC1,EC2,EC3,EC4,EC5,EC6"', allow_blank=True)
    sc.add_data_validation(dv2)
    dv2.add(f"K2:K{last}")

    sm = wb.create_sheet("Summary", 1)
    rng_d, rng_r = f"Screening!$J$2:$J${last}", f"Screening!$K$2:$K${last}"
    rows = [("Decisions in this batch", None), ("Records", len(batch)),
            ("Include", f'=COUNTIF({rng_d},"Include")'), ("Maybe", f'=COUNTIF({rng_d},"Maybe")'),
            ("Exclude", f'=COUNTIF({rng_d},"Exclude")'), ("Not yet decided", "=B2-SUM(B3:B5)"),
            ("Excluded without a reason (fix these)", f'=COUNTIFS({rng_d},"Exclude",{rng_r},"")'),
            (None, None), ("Exclusions by reason", None)]
    rows += [(f"EC{i}", f'=COUNTIFS({rng_d},"Exclude",{rng_r},"EC{i}")') for i in range(1, 7)]
    for i, (a, b) in enumerate(rows, 1):
        sm.cell(row=i, column=1, value=a).font = FB if b is None else F
        sm.cell(row=i, column=2, value=b).font = F
    sm.column_dimensions["A"].width = 38

    if pilot:
        ru = wb.create_sheet("Rules")
        ru.append(["Situation", "Agreed decision", "Example record ID"])
        for c in ru[1]:
            c.font = FH
            c.fill = HF
        ru.append(["Example: two metaheuristics combined (GA + PSO), no other family", "Exclude, EC1", ""])
        for c in ru[2]:
            c.font = Font(name="Arial", size=10, italic=True)
        for r_ in SCOPE_RULES:
            ru.append(list(r_))
        for row in ru.iter_rows(min_row=3):
            for c in row:
                c.font = F
                c.alignment = Alignment(wrap_text=True, vertical="top")
        for col, w in zip("ABC", [70, 20, 18]):
            ru.column_dimensions[col].width = w
    cr = wb.create_sheet("Criteria")
    cr.append(["ID", "Criterion"])
    for r in CRITERIA:
        cr.append(list(r))
    for c in cr[1]:
        c.font = FH
        c.fill = HF
    for row in cr.iter_rows(min_row=2):
        for c in row:
            c.font = F
            c.alignment = Alignment(wrap_text=True, vertical="top")
    cr.column_dimensions["A"].width = 8
    cr.column_dimensions["B"].width = 110
    wb.save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--records", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", type=int, default=2000)
    ap.add_argument("--reviewer", required=True, help="reviewer name shown in the workbooks")
    ap.add_argument("--tag", required=True, help="short reviewer code used in file names, e.g. ZA")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    k = pd.read_csv(a.records, dtype=str, keep_default_na=False)
    pilot = k.sample(n=100, random_state=2026)
    build(pilot, 0, 0, os.path.join(a.out, f"pilot_{a.tag}.xlsx"), 1, a.reviewer, a.tag, pilot=True)
    k["_strong"] = (k["all_blocks"] == "Y").astype(int)
    k["_year"] = pd.to_numeric(k["year"], errors="coerce").fillna(0)
    k = k.sort_values(["_strong", "_year", "record_id"], ascending=[False, False, True]).reset_index(drop=True)
    n = math.ceil(len(k) / a.size)
    for b in range(n):
        part = k.iloc[b * a.size:(b + 1) * a.size]
        path = os.path.join(a.out, f"screening_{a.tag}_batch_{b + 1:02d}.xlsx")
        build(part, b + 1, n, path, b * a.size + 1, a.reviewer, a.tag)
        print(path, len(part), "strong matches:", int(part["_strong"].sum()))


if __name__ == "__main__":
    main()
