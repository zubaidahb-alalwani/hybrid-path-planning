#!/usr/bin/env python3
"""
make_fulltext_workbooks.py -- full-text assessment workbooks.

Reviewer 1 assesses every report sought for retrieval (full_text_list); reviewer 2 independently
assesses a random sample (default 20%, seed 2026). The sample workbook shows no decision of reviewer 1.

USAGE
  python make_fulltext_workbooks.py --list screening_results/full_text_list_ZA.csv \
      --records merged/records_for_screening.csv --out fulltext --size 500 --sample 0.20
"""
import argparse, math, os
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation
from make_screening_batches import CRITERIA, SCOPE_RULES

F = Font(name="Arial", size=10); FB = Font(name="Arial", size=10, bold=True); FT = Font(name="Arial", size=12, bold=True)
FH = Font(name="Arial", size=10, bold=True, color="FFFFFFFF"); HF = PatternFill("solid", fgColor="FF1F4E79")
YF = PatternFill("solid", fgColor="FFFFF2CC"); THIN = Side(style="thin", color="FFBFBFBF")
COLS = ["No", "Record ID", "Title", "Authors", "Year", "Venue", "DOI", "Link", "Full text retrieved",
        "Decision", "Reason (EC)", "Families (e.g. F1+F3)", "Note", "References to check (citation searching)"]
WIDTHS = [6, 9, 45, 28, 6, 24, 22, 26, 11, 11, 10, 14, 36, 30]
INPUT = (8, 9, 10, 11, 12, 13)          # 0-based indexes of the yellow columns


def build(df, path, reviewer, tag, title):
    wb = Workbook(); ws = wb.active; ws.title = "Instructions"
    lines = [(f"{title}: reviewer {reviewer} ({tag})", FT),
             ("Read the full text of each report yourself and decide on your own; do not use keyword tools or look at the other "
              "reviewer's files. Fill only the yellow columns.", F), ("", F),
             ("Full text retrieved: Yes, or No if the full text could not be obtained (then leave Decision empty).", F),
             ("Decision: Include if the study meets all of IC1-IC4; otherwise Exclude with the first criterion that fails, "
              "EC1 to EC6 (manipulator or robot-arm planning is always EC3). There is no Maybe at this stage.", F),
             ("Families: the method families of the included study (F1 graph search, F2 sampling, F3 reactive, F4 optimization, "
              "F5 metaheuristic, F6 learning/AI).", F),
             ("References to check: for included studies, cited or citing papers that look eligible and may be missing from the search.", F)]
    for i, (t, f) in enumerate(lines, 1):
        c = ws.cell(row=i, column=1, value=t); c.font = f; c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["A"].width = 120
    sc = wb.create_sheet("Assessment", 1); sc.append(COLS)
    for i, (_, r) in enumerate(df.iterrows(), 1):
        link = f"https://doi.org/{r['doi']}" if r["doi"] else r["url"]
        sc.append([i, r["record_id"], r["title"], r["authors"][:200], int(r["year"]) if str(r["year"]).isdigit() else r["year"],
                   r["venue"], r["doi"], link, None, None, None, None, None, None])
    for c in sc[1]: c.font = FH; c.fill = HF; c.alignment = Alignment(wrap_text=True, vertical="center")
    last = len(df) + 1
    for row in sc.iter_rows(min_row=2, max_row=last):
        for c in row: c.font = F; c.alignment = Alignment(wrap_text=True, vertical="top"); c.border = Border(bottom=THIN)
        for j in INPUT: row[j].fill = YF
    for col, w in zip("ABCDEFGHIJKLMN", WIDTHS): sc.column_dimensions[col].width = w
    sc.freeze_panes = "D2"; sc.auto_filter.ref = f"A1:N{last}"
    for rng, opts in ((f"I2:I{last}", "Yes,No"), (f"J2:J{last}", "Include,Exclude"), (f"K2:K{last}", "EC1,EC2,EC3,EC4,EC5,EC6")):
        dv = DataValidation(type="list", formula1=f'"{opts}"', allow_blank=True); sc.add_data_validation(dv); dv.add(rng)
    sm = wb.create_sheet("Summary", 1); rd, rr, rt = (f"Assessment!$J$2:$J${last}", f"Assessment!$K$2:$K${last}", f"Assessment!$I$2:$I${last}")
    rows = [("Reports", len(df)), ("Not retrieved", f'=COUNTIF({rt},"No")'), ("Include", f'=COUNTIF({rd},"Include")'),
            ("Exclude", f'=COUNTIF({rd},"Exclude")'), ("Not yet decided", "=B1-B2-B3-B4"),
            ("Excluded without a reason (fix these)", f'=COUNTIFS({rd},"Exclude",{rr},"")'), (None, None), ("Exclusions by reason", None)]
    rows += [(f"EC{i}", f'=COUNTIFS({rd},"Exclude",{rr},"EC{i}")') for i in range(1, 7)]
    for i, (a, b) in enumerate(rows, 1):
        sm.cell(row=i, column=1, value=a).font = FB if b is None else F; sm.cell(row=i, column=2, value=b).font = F
    sm.column_dimensions["A"].width = 38
    cr = wb.create_sheet("Criteria"); cr.append(["ID", "Criterion"])
    for r in CRITERIA: cr.append(list(r))
    cr.append([]); cr.append(["Rule", "Agreed decision"])
    for r in SCOPE_RULES: cr.append([r[0], r[1]])
    for row in cr.iter_rows():
        for c in row: c.font = F; c.alignment = Alignment(wrap_text=True, vertical="top")
    for c in cr[1]: c.font = FH; c.fill = HF
    cr.column_dimensions["A"].width = 40; cr.column_dimensions["B"].width = 100
    wb.save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", required=True); ap.add_argument("--records", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--size", type=int, default=500); ap.add_argument("--sample", type=float, default=0.20)
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    ids = pd.read_csv(a.list, dtype=str, keep_default_na=False)["record_id"]
    k = pd.read_csv(a.records, dtype=str, keep_default_na=False).set_index("record_id").loc[ids].reset_index()
    k = k.sort_values("record_id").reset_index(drop=True)
    n = math.ceil(len(k) / a.size)
    for b in range(n):
        build(k.iloc[b * a.size:(b + 1) * a.size], os.path.join(a.out, f"fulltext_ZA_batch_{b + 1:02d}.xlsx"),
              "Zubaidah B. Alalwani", "ZA", f"Full-text assessment, batch {b + 1} of {n}")
    s = k.sample(frac=a.sample, random_state=2026).sample(frac=1, random_state=11).reset_index(drop=True)
    build(s, os.path.join(a.out, "fulltext_sample_WA.xlsx"), "Waleed Al-Ashtari", "WA",
          f"Full-text assessment, random {a.sample:.0%} sample ({len(s)} reports)")
    s[["record_id"]].to_csv(os.path.join(a.out, "fulltext_sample_ids.csv"), index=False)
    print(f"{n} batches for ZA ({len(k)} reports); sample for WA: {len(s)}")


if __name__ == "__main__":
    main()
