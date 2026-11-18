"""Build data/mapped_studies.csv from the classification master.

Input : search/5_classification/classification_master_ZA.csv  (all 4,546 reports sought)
        search/2_deduplication/records_for_screening.csv            (bibliographic data, document type)
Output: data/mapped_studies.csv                            (one row per mapped study, read by Figs. 3-8)

Coding rules
- only Decision == Include is mapped;
- families: '+'-separated codes -> sorted unique, ';'-separated;
- integration and level are kept for the full-text set only ('?' for the abstract set),
  because abstracts rarely state how the components are combined;
- 'Not reported' -> '?';
- venue_type from the database document type (conference vs journal).
Run from the project root:  python tools/build_mapped.py
"""
import os
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
m = pd.read_csv(os.path.join(ROOT, "search/5_classification/classification_master_ZA.csv"), dtype=str)
r = pd.read_csv(os.path.join(ROOT, "search/2_deduplication/records_for_screening.csv"), dtype=str,
                usecols=["record_id", "doc_type"])
m = m.merge(r, left_on="Record ID", right_on="record_id", how="left")
inc = m[m["Decision"] == "Include"].copy()

INT = {"Sequential": "S", "Embedded": "E", "Parallel": "P"}
LEV = {"Global": "G", "Local": "L", "Layered": "G-L"}
ENV = {"Static": "static", "Dynamic": "dynamic", "Both": "both"}
REAL = {"Yes": "Y", "No": "N"}


def fam(s):
    return ";".join(sorted(set(str(s).replace(" ", "").split("+"))))


def venue(doc):
    d = str(doc).lower()
    return "Conference" if "conference" in d else "Journal"


ft = inc["Basis"] == "Full text"
out = pd.DataFrame({
    "key": inc["Record ID"],
    "year": inc["Year"].str.replace(r"\.0$", "", regex=True),
    "methods": inc["Title"],
    "families": inc["Families (e.g. F1+F3)"].map(fam),
    "integration": [INT.get(v, "?") if f else "?" for v, f in zip(inc["Integration"], ft)],
    "level": [LEV.get(v, "?") if f else "?" for v, f in zip(inc["Level"], ft)],
    "environment": inc["Environment"].map(ENV).fillna("?"),
    "dimension": "?",
    "platform": inc["Platform"],
    "real": inc["Physical experiments"].map(REAL).fillna("?"),
    "metrics": "n.c.",
    "include": "Y",
    "basis": ["FT" if f else "Abs" for f in ft],
    "venue_type": inc["doc_type"].map(venue),
    "finding": "",
})
bad = out[~out["families"].str.fullmatch(r"F[1-6](;F[1-6])+")]
assert bad.empty, f"invalid family codes: {bad['key'].tolist()}"
assert set(out["platform"]) <= {"UGV", "UAV", "Car", "Marine", "Generic"}, set(out["platform"])
out.to_csv(os.path.join(ROOT, "data/mapped_studies.csv"), index=False)
print(f"mapped studies: {len(out)} (full text {int(ft.sum())}, abstract {int((~ft).sum())})")
