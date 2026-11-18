"""Two sensitivity analyses of the map.

(1) Full-text set versus abstract set: main findings recomputed on the 820 studies classified from full text,
    the 1,875 classified from title, abstract and keywords, and all 2,695 mapped studies.
(2) Fuzzy logic and ANFIS recoded from learning (F6) to reactive (F3): studies coded F6 whose title or abstract
    names fuzzy logic or ANFIS and no other learning method have F6 replaced by F3; studies naming fuzzy logic
    together with another learning method keep F6 and gain F3. Class sizes before and after are compared.
Outputs: data/sensitivity_sets.csv, data/sensitivity_fuzzy.csv, tables/sensitivity_table.tex
Run from the project root:  python tools/sensitivity.py
"""
import os, re, sys
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "figures"))
from _common import load, class_code, fam_list, FAMILIES  # noqa: E402

d = load("hybrids")
rec = pd.read_csv(os.path.join(ROOT, "search/2_deduplication/records_for_screening.csv"), dtype=str,
                  usecols=["record_id", "abstract"]).fillna("").set_index("record_id")
d = d.join(rec, on="key")
d["txt"] = d["methods"].fillna("") + " " + d["abstract"].fillna("")
d["C"] = d["cls"].where(d["cls"].str.count(r"\+") == 1, "Three or more")


def fmt(k, n):
    return f"{round(100 * k / n)} ({k:,}/{n:,})" if n else "--"


def profile(s):
    env = s[s["environment"] != "?"]
    real = s[s["real"] != "?"]
    ft = s[s["integration"] != "?"]
    sizes = s["C"].value_counts()
    two = sizes.drop("Three or more", errors="ignore")
    out = {"Studies": f"{len(s):,}"}
    for f, name in zip(FAMILIES, ["graph search", "sampling", "reactive", "optimization", "metaheuristic", "learning"]):
        out[f"Containing {name} (F{f[1]})"] = fmt(int(s["families"].str.contains(f).sum()), len(s))
    out["Three or more families"] = fmt(int((s["C"] == "Three or more").sum()), len(s))
    out["Three largest two-family classes"] = ", ".join(f"{c} ({n})" for c, n in two.head(3).items())
    out["Published 2023--2025"] = fmt(int((s["year"].astype(int) >= 2023).sum()), len(s))
    out["Moving obstacles (of studies stating the environment)"] = fmt(int(env["environment"].isin(["dynamic", "both"]).sum()), len(env))
    out["Physical experiments (of studies stating whether run)"] = fmt(int((real["real"] == "Y").sum()), len(real))
    out["Sequential integration (of full-text studies stating it)"] = fmt(int((ft["integration"] == "S").sum()), len(ft)) if len(ft) else "not charted"
    return out, sizes


sets = {"All mapped": d, "Full-text set": d[d["basis"] == "FT"], "Abstract set": d[d["basis"] == "Abs"]}
prof, sizes = {}, {}
for k, s in sets.items():
    prof[k], sizes[k] = profile(s)
tab = pd.DataFrame(prof)
# rank agreement of the fifteen two-family class sizes
two = [c for c in sizes["All mapped"].index if c != "Three or more"]
r_ft = sizes["Full-text set"].reindex(two).fillna(0).rank(ascending=False)
r_ab = sizes["Abstract set"].reindex(two).fillna(0).rank(ascending=False)
rho = r_ft.corr(r_ab, method="pearson")   # Spearman = Pearson on ranks
tab.loc["Rank correlation of class sizes with the other set (Spearman $\\rho$)"] = ["--", f"{rho:.2f}", f"{rho:.2f}"]
tab.to_csv(os.path.join(ROOT, "data", "sensitivity_sets.csv"))

# ---- (2) fuzzy / ANFIS recode ------------------------------------------------------------------
FUZZY = r"fuzzy|ANFIS"
OTHER_LEARN = r"neural|reinforcement|Q-learning|\bDQN\b|\bDRL\b|\bPPO\b|\bSAC\b|\bTD3\b|DDPG|deep learning|\bCNN\b|\bLSTM\b|transformer|imitation|supervised|Gaussian process"
f6 = d["families"].str.contains("F6")
fz = d["txt"].str.contains(FUZZY, flags=re.I, regex=True)
ol = d["txt"].str.contains(OTHER_LEARN, flags=re.I, regex=True)


def recode(row):
    fams = fam_list(row["families"])
    if "F6" not in fams or not re.search(FUZZY, row["txt"], re.I):
        return row["families"]
    if re.search(OTHER_LEARN, row["txt"], re.I):
        new = fams + ["F3"]                 # fuzzy plus another learning method: keep F6, add F3
    else:
        new = ["F3" if f == "F6" else f for f in fams]
    return ";".join(sorted(set(new), key=FAMILIES.index)) if len(set(new)) > 1 else ";".join(new)


d["families_r"] = d.apply(recode, axis=1)
d["cls_r"] = d["families_r"].apply(lambda s: class_code(fam_list(s)))
d["C_r"] = d["cls_r"].where(d["cls_r"].str.count(r"\+") == 1, "Three or more")
d.loc[~d["cls_r"].str.startswith("H["), "C_r"] = "Not a hybrid"
aff = d[f6 & fz]
chg = d[d["cls"] != d["cls_r"]]
before, after = d["C"].value_counts(), d["C_r"].value_counts()
cmp_ = pd.DataFrame({"before": before, "after": after}).fillna(0).astype(int)
cmp_["change"] = cmp_["after"] - cmp_["before"]
cmp_["rank_before"] = cmp_["before"].rank(ascending=False, method="min").astype(int)
cmp_["rank_after"] = cmp_["after"].rank(ascending=False, method="min").astype(int)
cmp_ = cmp_.sort_values("before", ascending=False)
cmp_.to_csv(os.path.join(ROOT, "data", "sensitivity_fuzzy.csv"))
fam_b = {f: round(100 * d["families"].str.contains(f).mean()) for f in FAMILIES}
fam_a = {f: round(100 * d["families_r"].str.contains(f).mean()) for f in FAMILIES}
summary = dict(n_f6=int(f6.sum()), n_fuzzy=len(aff), n_fuzzy_only=int((f6 & fz & ~ol).sum()),
               n_changed=len(chg), n_not_hybrid=int((d["C_r"] == "Not a hybrid").sum()),
               fam_before=fam_b, fam_after=fam_a)
pd.Series(summary).to_json(os.path.join(ROOT, "data", "sensitivity_fuzzy_summary.json"))

# ---- LaTeX table (sets) --------------------------------------------------------------------------
lines = []
for idx, r in tab.iterrows():
    lines.append(f"{idx} & {r['All mapped']} & {r['Full-text set']} & {r['Abstract set']} \\\\")
TEX = r"""\begin{table*}[!t]
\caption{Main Findings in the Full-Text Set, the Abstract Set, and All Mapped Studies}
\label{tab:sensitivity}
\centering
\footnotesize
\setlength{\tabcolsep}{4pt}
\begin{tabularx}{\textwidth}{@{}L{5.4cm} Y Y Y@{}}
\toprule
 & All mapped & Full-text set & Abstract set \\
\midrule
%s
\bottomrule
\multicolumn{4}{@{}p{0.97\textwidth}@{}}{\scriptsize Cells give the percentage followed by numerator/denominator. Denominators: all studies of the set for family shares, multi-family share, and year; studies that state their environment for moving obstacles; studies that state whether physical experiments were run for physical experiments; full-text studies for integration strategy, which was not charted from abstracts. Class codes as in Table~\ref{tab:classes}.}\\
\end{tabularx}
\end{table*}
"""
with open(os.path.join(ROOT, "tables", "sensitivity_table.tex"), "w") as f:
    f.write(TEX.replace("%s", "\n".join(lines).replace("%", r"\%").replace("H[", "H[")))
print(tab.to_string()); print(); print(summary); print(cmp_.to_string())
print(chg[["key", "families", "families_r", "cls", "cls_r"]].head(40).to_string())
