"""Refreshes the data sheets of Supplementary Material S3 (data/S3_coded_data.xlsx) from the current map.

Rewritten sheets: Mapped studies, Class profile, Co-occurrence, Dynamic profile, Evaluation mentions.
Updated cells: the PRISMA flow counts that depend on classification (EC1-EC6 full-text exclusions,
abstract-set exclusions). Codebook, Search log, Pair queries, TA sample forwarded and Algorithm counts
are left as they are. Run after tools/build_all.py:  python tools/update_s3.py
"""
import os, sys
import pandas as pd
import openpyxl
from openpyxl.styles import Font

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "figures"))
from _common import class_code, fam_list  # noqa: E402

P = os.path.join(ROOT, "data", "S3_coded_data.xlsx")
wb = openpyxl.load_workbook(P)

# ---- Mapped studies --------------------------------------------------------------------------
m = pd.read_csv(os.path.join(ROOT, "data", "mapped_studies.csv"), keep_default_na=False)
rec = pd.read_csv(os.path.join(ROOT, "search/2_deduplication/records_for_screening.csv"), dtype=str,
                  usecols=["record_id", "title", "authors", "venue", "doi"]).fillna("").set_index("record_id")
ex = set(pd.read_csv(os.path.join(ROOT, "data", "section5_examples.csv"))["record_id"])
LEV = {"G-L": "G-L"}
rows = []
for r in m.itertuples():
    x = rec.loc[r.key]
    rows.append([r.key, r.basis, int(r.year), x["title"], x["authors"], x["venue"], r.venue_type, x["doi"],
                 r.families, class_code(fam_list(r.families)), r.platform, r.environment,
                 r.integration, LEV.get(r.level, r.level), r.real, "Yes" if r.key in ex else ""])
ws = wb["Mapped studies"]
hdr = [c.value for c in ws[1]]
ws.delete_rows(2, ws.max_row)
for row in rows:
    ws.append(row[:len(hdr)])
print("Mapped studies:", len(rows))


def replace_sheet(name, note, df, index=None):
    pos = wb.sheetnames.index(name) if name in wb.sheetnames else len(wb.sheetnames)
    if name in wb.sheetnames:
        del wb[name]
    s = wb.create_sheet(name, pos)
    s.append([note]); s.append([])
    s.append(([""] if index is not None else []) + list(df.columns))
    for c in s[3]:
        c.font = Font(bold=True)
    for i, row in zip(df.index, df.itertuples(index=False)):
        s.append(([index.get(i, i)] if index is not None else []) + [v.item() if hasattr(v, "item") else v for v in row])


replace_sheet("Class profile", "Per-class profile (manuscript Table 6), from tools/class_profile.py. Integration and level: full-text set only; "
              "dyn_pct and real_pct among studies where stated; component columns: % of titles and abstracts naming the algorithm (a proxy).",
              pd.read_csv(os.path.join(ROOT, "data", "class_profile.csv")))
co = pd.read_csv(os.path.join(ROOT, "data", "fig4_cooccurrence_matrix.csv"), index_col=0)
names = {"F1": "F1 Graph search", "F2": "F2 Sampling", "F3": "F3 Reactive", "F4": "F4 Optimization",
         "F5": "F5 Metaheuristic", "F6": "F6 Learning/AI"}
replace_sheet("Co-occurrence", f"Family co-occurrence in the {len(m):,} mapped studies (manuscript Figure 4): each study counts once for every unordered pair "
              "of distinct families it contains. From figures/fig4_cooccurrence.py.", co, index=names)
replace_sheet("Dynamic profile", "Per class (manuscript Table 7). N: mapped studies in the class; N_env: studies that state their test environment; "
              "N_dyn: studies tested with moving obstacles (dynamic, or both static and dynamic); dyn_pct: N_dyn as a percentage of N_env. "
              "prediction, learned prediction, VO/ORCA, replanning: percentage of the N_dyn studies whose title or abstract names motion "
              "prediction or forecasting ('predictive' excluded), a learned predictor (e.g., LSTM, transformer, neural network), velocity "
              "obstacles or ORCA, or replanning; counted after classification with fixed search terms (tools/evaluation_profile.py), so they "
              "are lower bounds; 0 means fewer than 0.5%. MULTI: three or more families; ALL: all mapped studies (percentages computed from the totals).",
              pd.read_csv(os.path.join(ROOT, "data", "dynamic_profile.csv")))
replace_sheet("Evaluation mentions", "Mapped studies whose title or abstract names each metric, benchmark or simulator (manuscript Section 4.4; S5, Tables S5-S6). "
              "From tools/evaluation_profile.py; lower bounds.", pd.read_csv(os.path.join(ROOT, "data", "evaluation_mentions.csv")))

replace_sheet("Sensitivity sets", "Main findings in all mapped studies, the full-text set and the abstract set (manuscript Table 8). "
              "Cells: percentage (numerator/denominator). From tools/sensitivity.py.",
              pd.read_csv(os.path.join(ROOT, "data", "sensitivity_sets.csv"), index_col=0), index={})
replace_sheet("Sensitivity fuzzy", "Class sizes before and after recoding fuzzy logic and ANFIS from learning (F6) to reactive (F3) "
              "(manuscript Section 4.5). Fuzzy logic stays in F6 in all reported results; no study was reclassified. Studies coded F6 whose title or abstract names fuzzy logic or ANFIS and no other learning method have F6 "
              "replaced by F3; those that also name another learning method keep F6 and gain F3. From tools/sensitivity.py.",
              pd.read_csv(os.path.join(ROOT, "data", "sensitivity_fuzzy.csv"), index_col=0), index={})

# ---- PRISMA flow counts that depend on classification -----------------------------------------
cm = pd.read_csv(os.path.join(ROOT, "search/5_classification/classification_master_ZA.csv"), dtype=str).fillna("")
ft = cm[cm["Basis"] == "Full text"]
ecs = ft[ft["Decision"] == "Exclude"]["Reason (EC)"].value_counts().to_dict()
n_abs = int(((cm["Basis"] != "Full text") & (cm["Decision"] == "Exclude")).sum())
ab = cm[(cm["Basis"] != "Full text") & (cm["Decision"] == "Exclude")]["Reason (EC)"].value_counts().to_dict()
abs_note = ("Classification from title, abstract and keywords (Z.B.A.); "
            + ", ".join(f"EC{i} {ab.get(f'EC{i}', 0)}" for i in range(1, 7)))
pf = wb["PRISMA flow"]
for row in pf.iter_rows(min_row=1):
    lab = str(row[0].value or "")
    for ec in ["EC1", "EC2", "EC3", "EC4", "EC5", "EC6"]:
        if lab.startswith(f"Excluded: {ec}"):
            row[1].value = int(ecs.get(ec, 0))
    if lab.startswith("Excluded after classification from title, abstract"):
        row[1].value = n_abs
        row[2].value = abs_note
wb.save(P)
print("PRISMA:", ecs, "abstract-set exclusions:", n_abs)
