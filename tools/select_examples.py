"""Selects the example studies of Section V from the map and checks data/section5_examples.csv against them.

Rule, for each two-family class and for the pooled multi-family group:
- candidates: mapped studies classified from full text, with a DOI and an abstract in the search records;
- target integration strategies: those used by at least 10% of the class's full-text studies, plus parallel (P) if present;
- target platforms: the three most frequent non-generic platforms of the class;
- ranking of candidates: physical experiments first, then journal articles, then more recent years;
- greedy choice: repeatedly take the highest-ranked candidate that adds the most uncovered targets
  (a new integration strategy counts 2, a new platform 1) until 2-4 studies are chosen
  (number of target strategies + 1, at least 2, at most 4); multi-family examples must differ in class code.
Run from the project root:  python tools/select_examples.py
"""
import os, sys
import pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "figures"))
from _common import load, class_order  # noqa: E402

d = load("hybrids", basis="FT")
r = pd.read_csv(os.path.join(ROOT, "search/2_deduplication/records_for_screening.csv"), dtype=str,
                usecols=["record_id", "doi", "abstract"]).fillna("").set_index("record_id")
d = d.join(r, on="key")
d = d[(d["abstract"].str.len() > 200) & (d["doi"] != "")]
d["C"] = d["cls"].where(d["cls"].str.count(r"\+") == 1, "MULTI")
chosen_all = []
for C in class_order([c for c in d["C"].unique() if c != "MULTI"]) + ["MULTI"]:
    s = d[d["C"] == C].copy()
    ints = [k for k, v in s["integration"].value_counts().items() if k != "?" and (v >= 0.1 * len(s) or k == "P")]
    plats = [k for k in s["platform"].value_counts().index if k != "Generic"][:3]
    s["score"] = (s["real"] == "Y") * 4 + (s["venue_type"] == "Journal") * 1 + s["year"].astype(int) / 10000
    s = s.sort_values(["score", "key"], ascending=[False, True])
    need = min(4, max(2, len(ints) + 1))
    chosen, ci, cp = [], set(), set()
    while len(chosen) < need:
        best, bg = None, -1
        for _, x in s.iterrows():
            if x["key"] in [y["key"] for y in chosen] or (C == "MULTI" and x["cls"] in [y["cls"] for y in chosen]):
                continue
            g = (x["integration"] in ints and x["integration"] not in ci) * 2 + (x["platform"] in plats and x["platform"] not in cp)
            if g > bg:
                best, bg = x, g
            if g == 3:
                break
        chosen.append(best); ci.add(best["integration"]); cp.add(best["platform"])
    chosen_all += [(C, x["key"]) for x in chosen]
sel = pd.DataFrame(chosen_all, columns=["class", "record_id"])
sel.to_csv(os.path.join(ROOT, "data", "section5_selection.csv"), index=False)
f = os.path.join(ROOT, "data", "section5_examples.csv")
if os.path.exists(f):
    have = set(pd.read_csv(f)["record_id"])
    print("selected:", len(sel), "| missing from section5_examples.csv:", sorted(set(sel["record_id"]) - have),
          "| extra:", sorted(have - set(sel["record_id"])))
