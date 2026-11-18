#!/usr/bin/env python3
"""
make_classification_workbooks.py -- classification workbooks for the systematic mapping study.

Every report sought for retrieval is classified: from the full text when it was obtained ("Full text"),
otherwise from title, abstract and keywords ("Abstract"). The retrieval status is copied from the filled
full-text batches. Reviewer 1 gets all reports; reviewer 2 gets the fixed random 20% sample, with no
decision of reviewer 1 shown.

USAGE
  python make_classification_workbooks.py --batches <folder with filled fulltext batches> \
      --records merged/records_for_screening.csv --sample fulltext/fulltext_sample_ids.csv --out classification
"""
import argparse, glob, os
import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation
from make_screening_batches import CRITERIA, SCOPE_RULES

F = Font(name="Arial", size=10); FB = Font(name="Arial", size=10, bold=True); FT = Font(name="Arial", size=12, bold=True)
FH = Font(name="Arial", size=10, bold=True, color="FFFFFFFF"); HF = PatternFill("solid", fgColor="FF1F4E79")
YF = PatternFill("solid", fgColor="FFFFF2CC"); GF = PatternFill("solid", fgColor="FFF2F2F2"); THIN = Side(style="thin", color="FFBFBFBF")
COLS = ["No", "Record ID", "Basis", "Title", "Year", "Venue", "Abstract", "Keywords", "DOI / link",
        "Decision", "Reason (EC)", "Families (e.g. F1+F3)", "Platform", "Environment", "Integration", "Level",
        "Physical experiments", "Note", "References to check"]
WIDTHS = [6, 9, 10, 40, 6, 22, 70, 26, 24, 11, 9, 13, 12, 12, 11, 9, 11, 32, 26]
LISTS = {"J": "Include,Exclude", "K": "EC1,EC2,EC3,EC4,EC5,EC6", "M": "UGV,UAV,Marine,Car,Generic,Not reported",
         "N": "Static,Dynamic,Both,Not reported", "O": "Sequential,Embedded,Parallel,Not reported",
         "P": "Global,Local,Layered,Not reported", "Q": "Yes,No,Not reported"}
INPUT = range(9, 19)


def build(df, path, reviewer, tag, title):
    wb = Workbook(); ws = wb.active; ws.title = "Instructions"
    lines = [(f"{title}: reviewer {reviewer} ({tag})", FT),
             ("Classify every report yourself, by reading it; do not use keyword or automated tools and do not look at the other "
              "reviewer's files. Fill only the yellow columns.", F), ("", F),
             ("Basis (grey, fixed): 'Full text' = read the full text; 'Abstract' = full text not obtainable, so judge and classify "
              "from the title, abstract and keywords shown in the row.", F),
             ("Decision: Include if the study meets IC1-IC4 (judged on the full text, or on the abstract for Basis = Abstract); "
              "otherwise Exclude with the first criterion that fails (EC1-EC6; manipulator or robot-arm planning is always EC3).", F),
             ("For included studies fill Families, Platform, Environment, Integration, Level and Physical experiments. "
              "For Basis = Abstract, choose 'Not reported' for anything the abstract does not state; never guess.", F),
             ("References to check: for included full-text studies, cited papers that look eligible (citation searching).", F)]
    for i, (t, f) in enumerate(lines, 1):
        c = ws.cell(row=i, column=1, value=t); c.font = f; c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["A"].width = 120
    sc = wb.create_sheet("Classification", 1); sc.append(COLS)
    for i, (_, r) in enumerate(df.iterrows(), 1):
        link = f"https://doi.org/{r['doi']}" if r["doi"] else r["url"]
        sc.append([i, r["record_id"], r["basis"], r["title"], int(r["year"]) if str(r["year"]).isdigit() else r["year"],
                   r["venue"], r["abstract"], r["keywords"][:300], link] + [None] * 10)
    for c in sc[1]: c.font = FH; c.fill = HF; c.alignment = Alignment(wrap_text=True, vertical="center")
    last = len(df) + 1
    for row in sc.iter_rows(min_row=2, max_row=last):
        for c in row: c.font = F; c.alignment = Alignment(wrap_text=True, vertical="top"); c.border = Border(bottom=THIN)
        row[2].fill = GF
        for j in INPUT: row[j].fill = YF
    for k, w in enumerate(WIDTHS): sc.column_dimensions[chr(65 + k)].width = w
    sc.freeze_panes = "E2"; sc.auto_filter.ref = f"A1:S{last}"
    for col, opts in LISTS.items():
        dv = DataValidation(type="list", formula1=f'"{opts}"', allow_blank=True); sc.add_data_validation(dv); dv.add(f"{col}2:{col}{last}")
    sm = wb.create_sheet("Summary", 1); d, r, b = (f"Classification!$J$2:$J${last}", f"Classification!$K$2:$K${last}", f"Classification!$C$2:$C${last}")
    rows = [("Reports", len(df)), ("Basis: full text", f'=COUNTIF({b},"Full text")'), ("Basis: abstract", f'=COUNTIF({b},"Abstract")'),
            ("Include (full text)", f'=COUNTIFS({b},"Full text",{d},"Include")'), ("Include (abstract)", f'=COUNTIFS({b},"Abstract",{d},"Include")'),
            ("Exclude (full text)", f'=COUNTIFS({b},"Full text",{d},"Exclude")'), ("Exclude (abstract)", f'=COUNTIFS({b},"Abstract",{d},"Exclude")'),
            ("Not yet decided", f'=B1-COUNTIF({d},"Include")-COUNTIF({d},"Exclude")'),
            ("Excluded without a reason (fix these)", f'=COUNTIFS({d},"Exclude",{r},"")'), (None, None), ("Exclusions by reason", None)]
    rows += [(f"EC{i}", f'=COUNTIFS({d},"Exclude",{r},"EC{i}")') for i in range(1, 7)]
    for i, (a, v) in enumerate(rows, 1):
        sm.cell(row=i, column=1, value=a).font = FB if v is None else F; sm.cell(row=i, column=2, value=v).font = F
    sm.column_dimensions["A"].width = 38
    cr = wb.create_sheet("Criteria"); cr.append(["ID", "Criterion"])
    for x in CRITERIA: cr.append(list(x))
    cr.append([]); cr.append(["Rule", "Agreed decision"])
    for x in SCOPE_RULES: cr.append([x[0], x[1]])
    cr.append([]); cr.append(["Families", "F1 graph search; F2 sampling; F3 reactive; F4 optimization; F5 metaheuristic; F6 learning/AI"])
    cr.append(["Integration", "Sequential (output of one feeds the next); Embedded (one runs inside the other's loop); Parallel (both run, outputs arbitrated)"])
    cr.append(["Level", "Global; Local; Layered (global + local)"])
    for row in cr.iter_rows():
        for c in row: c.font = F; c.alignment = Alignment(wrap_text=True, vertical="top")
    for c in cr[1]: c.font = FH; c.fill = HF
    cr.column_dimensions["A"].width = 40; cr.column_dimensions["B"].width = 100
    wb.save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--batches", required=True); ap.add_argument("--records", required=True)
    ap.add_argument("--sample", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    k = pd.read_csv(a.records, dtype=str, keep_default_na=False).set_index("record_id")
    files = sorted(glob.glob(os.path.join(a.batches, "*.xlsx")))
    allrows = []
    for n, f in enumerate(files, 1):
        ws = load_workbook(f, read_only=True, data_only=True)["Assessment"]
        it = ws.iter_rows(values_only=True); hdr = list(next(it))
        ids = [(r[hdr.index("Record ID")], r[hdr.index("Full text retrieved")]) for r in it if r[1]]
        df = k.loc[[i for i, _ in ids]].reset_index()
        df["basis"] = ["Full text" if str(v).strip() == "Yes" else "Abstract" for _, v in ids]
        build(df, os.path.join(a.out, f"classification_ZA_batch_{n:02d}.xlsx"), "Zubaidah B. Alalwani", "ZA",
              f"Classification, batch {n} of {len(files)}")
        allrows.append(df)
        print(os.path.basename(f), "->", n, len(df), df["basis"].value_counts().to_dict())
    alld = pd.concat(allrows).set_index("record_id")
    sid = pd.read_csv(a.sample, dtype=str)["record_id"]
    s = alld.loc[sid].reset_index()
    build(s, os.path.join(a.out, "classification_sample_WA.xlsx"), "Waleed Al-Ashtari", "WA",
          f"Classification, random 20% sample ({len(s)} reports)")
    print("WA sample", len(s), s["basis"].value_counts().to_dict())


if __name__ == "__main__":
    main()
