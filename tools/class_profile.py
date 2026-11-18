"""Profile of each hybrid class computed from the map, and the class-overview table of Section V.

Input : data/mapped_studies.csv, search/2_deduplication/records_for_screening.csv (titles and abstracts)
Output: data/class_profile.csv        (one row per two-family class plus the pooled multi-family group)
        tables/class_overview.tex      (Table "Hybrid classes in the map", Section V-C)

Columns
- N, FT: mapped studies and those classified from full text;
- S/E/P: integration strategy among full-text studies (sequential, embedded, parallel);
- G/L/GL: planning level among full-text studies;
- dyn_pct: share with moving obstacles among studies that state the environment;
- real_pct: share reporting physical experiments among studies where this was coded;
- n1519, n2022, n2325: studies by period;
- top platforms; component mentions = share of titles+abstracts naming each algorithm
  (regular expressions below; a mention is a proxy for use, not a coded variable).
Run from the project root:  python tools/class_profile.py
"""
import os, re, sys
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "figures"))
from _common import load, class_order  # noqa: E402

KEYS = {
    "A*": r"\bA\s?\*|\bA-?star\b|\bA star\b", "Dijkstra": r"dijkstra", "JPS": r"jump point",
    "Hybrid A*": r"hybrid a\s?\*", "RRT": r"\bRRT", "PRM": r"\bPRM\b|probabilistic road",
    "APF": r"potential field|\bAPF\b", "DWA": r"dynamic window|\bDWA\b", "TEB": r"elastic band|\bTEB\b",
    "ORCA/VO": r"velocity obstacle|\bORCA\b|\bRVO\b", "fuzzy": r"fuzzy",
    "MPC": r"model predictive|\bMPC\b|\bNMPC\b",
    "traj. opt.": r"quadratic program|minimum.snap|B-?spline optim|trajectory optimi",
    "GA": r"genetic algorithm|\bGA\b", "PSO": r"particle swarm|\bPSO\b", "ACO": r"ant colony|\bACO\b",
    "GWO": r"grey wolf|gray wolf|\bGWO\b",
    "RL": r"reinforcement learning|Q-learning|\bDQN\b|\bDRL\b|\bPPO\b|\bSAC\b|\bTD3\b|DDPG",
    "NN": r"neural network|deep learning|\bCNN\b|\bLSTM\b|transformer",
}

d = load("hybrids")
rec = pd.read_csv(os.path.join(ROOT, "search/2_deduplication/records_for_screening.csv"), dtype=str,
                  usecols=["record_id", "abstract"]).fillna("").set_index("record_id")
d = d.join(rec, on="key")
d["txt"] = d["methods"].fillna("") + " " + d["abstract"].fillna("")
d["y"] = d["year"].astype(int)
d["C"] = d["cls"].where(d["cls"].str.count(r"\+") == 1, "MULTI")

rows = []
for C in class_order([c for c in d["C"].unique() if c != "MULTI"]) + ["MULTI"]:
    s = d[d["C"] == C]
    ft = s[s["basis"] == "FT"]
    env = s[s["environment"] != "?"]
    real = s[s["real"] != "?"]
    i, l = ft["integration"].value_counts(), ft["level"].value_counts()
    row = dict(cls=C, N=len(s), FT=len(ft), S=i.get("S", 0), E=i.get("E", 0), P=i.get("P", 0),
               G=l.get("G", 0), L=l.get("L", 0), GL=l.get("G-L", 0),
               dyn_pct=round(100 * env["environment"].isin(["dynamic", "both"]).mean()),
               real_pct=round(100 * (real["real"] == "Y").mean()),
               n1519=int((s["y"] <= 2019).sum()), n2022=int(s["y"].between(2020, 2022).sum()),
               n2325=int((s["y"] >= 2023).sum()),
               platforms="; ".join(f"{k} {v}" for k, v in s["platform"].value_counts().head(3).items()))
    for k, p in KEYS.items():
        row[k] = round(100 * s["txt"].str.contains(p, flags=re.I, regex=True).mean())
    rows.append(row)
t = pd.DataFrame(rows)
t.to_csv(os.path.join(ROOT, "data", "class_profile.csv"), index=False)

# ---- LaTeX table ------------------------------------------------------------------------------
NAMES = {"1": "Graph", "2": "Sampl.", "3": "React.", "4": "Optim.", "5": "Meta.", "6": "Learn."}
LEVN = {"G": "G", "L": "L", "GL": "G--L"}


def top_components(r, n=4):
    v = sorted(((r[k], k) for k in KEYS), reverse=True)
    return ", ".join(f"{k} {p}" for p, k in v[:n] if p >= 10)


lines = []
for _, r in t.iterrows():
    if r["cls"] == "MULTI":
        name = "Three or more"
    else:
        a, b = r["cls"][2:-1].split("+")
        name = f'{r["cls"]} {NAMES[a]}+{NAMES[b]}'
    ft = max(1, r["FT"])
    integ = "/".join(f'{x} {round(100 * r[x] / ft)}' for x in ["S", "E", "P"] if r[x] > 0)
    lev = max(["G", "L", "GL"], key=lambda x: r[x])
    plats = ", ".join(r["platforms"].split("; ")[:2])   # two most frequent platforms (all three in class_profile.csv)
    lines.append(f'{name} & {r["N"]} ({r["FT"]}) & {r["n1519"]}/{r["n2022"]}/{r["n2325"]} & {integ} & '
                 f'{LEVN[lev]} & {r["dyn_pct"]} & {r["real_pct"]} & {plats} & {top_components(r)} \\\\')

TEX = r"""\begin{table*}[!t]
\caption{The Hybrid Classes in the Map (%s Studies)}
\label{tab:classes}
\centering
\scriptsize
\setlength{\tabcolsep}{3pt}
\renewcommand{\arraystretch}{1.08}
\begin{tabularx}{\textwidth}{@{}L{2.45cm} c c L{1.75cm} c c c L{2.3cm} Y@{}}
\toprule
Class & $N$ (FT) & Studies by period & Integration, \%% (FT) & Level & Mov.\,\%% & Phys.\,\%% & Top platforms & Components named in title or abstract, \%% \\
\midrule
%s
\bottomrule
\multicolumn{9}{@{}p{0.97\textwidth}@{}}{\scriptsize $N$: mapped studies; FT: classified from full text. Studies by period: mapped studies published in 2015--2019 / 2020--2022 / 2023--2025. Integration (S sequential, E embedded, P parallel) and the most frequent planning level (G global, L local, G--L layered) are charted for the full-text set only. Mov.: share of studies with moving obstacles among those that state the environment. Phys.: share reporting physical experiments among studies where this was charted. Components: share of titles and abstracts naming each algorithm (shares of at least 10\%%; a proxy, not a charted variable).}\\
\end{tabularx}
\end{table*}
"""
n = f"{len(d):,}".replace(",", "{,}")
with open(os.path.join(ROOT, "tables", "class_overview.tex"), "w") as f:
    f.write(TEX % (n, "\n".join(lines)))
print(t[["cls", "N", "FT", "S", "E", "P", "dyn_pct", "real_pct"]].to_string(index=False))
