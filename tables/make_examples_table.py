"""Generates tables/examples_table.tex: the example studies of Section V, all drawn from the map.

Input : data/section5_examples.csv  (record_id, bibkey, combined methods written from title and abstract)
        data/mapped_studies.csv      (class, integration, level, environment, platform, physical experiments)
Selection rule (Section V-C): for each two-family class and for the multi-family group, two to four
studies from the full-text set that together cover the integration strategies used by at least 10% of
the class's full-text studies (and any parallel one) and its most frequent non-generic platforms,
preferring studies with physical experiments, journal articles, and recent years; multi-family examples
have distinct class codes. Implemented in tools/select_examples.py.
Run from the project root:  python tables/make_examples_table.py
"""
import os, sys, re
import pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "figures"))
from _common import load, class_order  # noqa: E402

ex = pd.read_csv(os.path.join(ROOT, "data", "section5_examples.csv"))
m = load("hybrids").drop(columns=["methods"]).set_index("key")
ex = ex.join(m, on="record_id")
assert ex["cls"].notna().all(), "an example is not in the map"
assert (ex["basis"] == "FT").all(), "examples must come from the full-text set"
ex["C"] = ex["cls"].where(ex["cls"].str.count(r"\+") == 1, "MULTI")
order = {c: i for i, c in enumerate(class_order([c for c in ex["C"].unique() if c != "MULTI"]) + ["MULTI"])}
ex = ex.assign(o=ex["C"].map(order)).sort_values(["o", "year", "bibkey"])
ENV = {"static": "S", "dynamic": "D", "both": "S+D", "?": "n.r."}
LEV = {"G-L": "G--L"}


def esc(s):
    s = str(s)
    for a, b in [("&", "\\&"), ("%", "\\%"), ("#", "\\#"), ("_", "\\_")]:
        s = s.replace(a, b)
    return s.replace("A*", "A$^*$").replace("RRT*", "RRT$^*$")


rows = [f'\\cite{{{r.bibkey}}} & {r.year} & {r.cls} & {esc(r.methods)} & {r.integration} & '
        f'{LEV.get(r.level, r.level)} & {ENV[r.environment]} & {r.platform} & {'n.r.' if r.real == '?' else r.real} \\\\'
        for r in ex.itertuples()]
HEAD = r"""\begin{table*}[!t]
\caption{%s}
%s
\centering
\scriptsize
\setlength{\tabcolsep}{3pt}
\renewcommand{\arraystretch}{1.04}
\begin{tabularx}{\textwidth}{@{}L{1.0cm} c L{1.35cm} Y c c c L{1.0cm} c@{}}
\toprule
Ref. & Year & Class & Combined methods (from title and abstract) & Int. & Level & Env. & Platform & Phys. \\
\midrule
"""
NOTE = (r"\multicolumn{9}{@{}p{0.97\textwidth}@{}}{\scriptsize All studies are mapped studies classified from full text; "
        r"class, integration (S sequential, E embedded, P parallel), level (G global, L local, G--L layered), environment "
        r"(S static, D dynamic, S+D both; n.r. not reported in the study), platform, and physical experiments (Phys.) are as charted in Supplementary Material S3. "
        r"Selection rule in Section~\ref{sec:hybrid-examples}.}\\")
half = 26
parts = [rows[:half], rows[half:]]
caps = ["Example Studies from the Map: Graph-Search and Sampling-Based Classes",
        "Example Studies from the Map: Reactive, Optimization, Metaheuristic, Learning, and Multi-Family Classes"]
labs = [r"\label{tab:examples}", r"\label{tab:examples2}"]
out = []
for p, c, l in zip(parts, caps, labs):
    out.append(HEAD % (c, l) + "\n".join(p) + "\n\\bottomrule\n" + NOTE + "\n\\end{tabularx}\n\\end{table*}\n")
with open(os.path.join(ROOT, "tables", "examples_table.tex"), "w") as f:
    f.write("\n".join(out))
print(len(rows), "examples;", ex.groupby("C").size().to_dict())
