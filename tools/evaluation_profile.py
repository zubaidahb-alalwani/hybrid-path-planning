"""Dynamic-obstacle handling and evaluation practice as stated in the titles and abstracts of the mapped studies.

Input : data/mapped_studies.csv, search/2_deduplication/records_for_screening.csv (abstracts)
Output: data/dynamic_profile.csv     per class, among studies with moving obstacles: share naming motion prediction,
                                      learned prediction, velocity obstacles/ORCA, and replanning (Table XII)
        data/evaluation_mentions.csv  number of titles+abstracts naming each metric, benchmark, or simulator
                                      (the counts in Tables XIII-XIV) and two baseline indicators
        tables/dynamic_table.tex      Table XII
Mentions are a proxy: an abstract that names a term usually uses it, but many studies use terms their abstract
does not name, so the shares are lower bounds and are compared across classes rather than read as absolute rates.
Run from the project root:  python tools/evaluation_profile.py
"""
import os, re, sys
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "figures"))
from _common import load, class_order  # noqa: E402

d = load("hybrids")
rec = pd.read_csv(os.path.join(ROOT, "search/2_deduplication/records_for_screening.csv"), dtype=str,
                  usecols=["record_id", "abstract"]).fillna("").set_index("record_id")
d = d.join(rec, on="key")
d["txt"] = d["methods"].fillna("") + " " + d["abstract"].fillna("")
d["C"] = d["cls"].where(d["cls"].str.count(r"\+") == 1, "MULTI")


def has(s, p):
    return s["txt"].str.contains(p, flags=re.I, regex=True)


# ---- dynamic handling (Table XII) -------------------------------------------------------------
DYN = {
    "prediction": r"predict(?!ive)|forecast|anticipat",          # 'predictive' (as in MPC) excluded
    "learned prediction": r"(?:LSTM|transformer|neural|learn)[^.]{0,60}(?:predict(?!ive)|trajectory forecast)",
    "VO/ORCA": r"velocity obstacle|\bORCA\b|\bRVO\b",
    "replanning": r"re-?plan",
}
rows = []
for C in class_order([c for c in d["C"].unique() if c != "MULTI"]) + ["MULTI", "ALL"]:
    s = d if C == "ALL" else d[d["C"] == C]
    env = s[s["environment"] != "?"]
    dyn = s[s["environment"].isin(["dynamic", "both"])]
    row = dict(cls=C, N=len(s), N_env=len(env), N_dyn=len(dyn),
               dyn_pct=round(100 * len(dyn) / max(1, len(env))))
    for k, p in DYN.items():
        row[k] = round(100 * has(dyn, p).mean()) if len(dyn) else 0
    rows.append(row)
dp = pd.DataFrame(rows)
dp.to_csv(os.path.join(ROOT, "data", "dynamic_profile.csv"), index=False)

lines = []
for _, r in dp.iterrows():
    name = {"MULTI": "Three or more", "ALL": r"\midrule All classes"}.get(r["cls"], r["cls"])
    small = r"$^{\ast}$" if r["N_dyn"] < 30 else ""
    lines.append(f'{name} & {r["N"]} & {r["N_env"]} & {r["dyn_pct"]} & {r["N_dyn"]}{small} & {r["prediction"]} & '
                 f'{r["learned prediction"]} & {r["VO/ORCA"]} & {r["replanning"]} \\\\')
TEX = r"""\begin{table}[!t]
\caption{Moving Obstacles and How They Are Handled, by Class}
\label{tab:dem}
\centering
\footnotesize
\setlength{\tabcolsep}{4pt}
\begin{tabular}{@{}l r r r r r r r r@{}}
\toprule
 & & & & & \multicolumn{4}{c}{Named in abstracts, \% of $N_{\mathrm{dyn}}$} \\
\cmidrule(l){6-9}
Class & $N$ & $N_{\mathrm{env}}$ & Dyn.\,\% & $N_{\mathrm{dyn}}$ & Pred. & Learned & VO & Replan \\
\midrule
%s
\bottomrule
\end{tabular}

\smallskip
\parbox{\columnwidth}{\scriptsize $N$: mapped studies in the class. $N_{\mathrm{env}}$: studies that state their test environment. $N_{\mathrm{dyn}}$: studies tested with moving obstacles (dynamic, or both static and dynamic). Dyn.\,\%: $N_{\mathrm{dyn}}$ as a share of $N_{\mathrm{env}}$. The last four columns are shares of $N_{\mathrm{dyn}}$ whose title or abstract names: Pred., motion prediction or forecasting (``predictive'' excluded); Learned, a learned predictor (e.g., LSTM, transformer, or neural network); VO, velocity obstacles or ORCA; Replan, replanning. They were counted after classification by searching titles and abstracts with fixed terms (released with the code), so they are lower bounds; 0 means fewer than 0.5\%. $^{\ast}$Fewer than 30 dynamic studies.}
\end{table}
"""
with open(os.path.join(ROOT, "tables", "dynamic_table.tex"), "w") as f:
    f.write(TEX.replace("%s", "\n".join(lines)))

# ---- evaluation mentions (Tables XIII-XIV) ---------------------------------------------------
METRICS = {
    "Path length": r"path length|length of the path|shorter path|path distance|path cost",
    "Computation time": r"(?:computation|computational|planning|running|search|execution|convergence|calculation) time|time cost|time consumption",
    "Success rate": r"success rate|success ratio|arrival rate",
    "Smoothness": r"smooth|turning (?:points|angle|times)|number of turns|inflection|curvature|jerk",
    "Clearance": r"clearance|safety distance|safe distance|safety margin|distance (?:to|from) (?:the )?obstacles?",
    "Energy": r"energy|fuel|power consumption",
    "Replanning": r"re-?plan",
    "Collision rate": r"collision rate|collision ratio|collision probability|number of collisions",
    "Memory": r"memory|expanded nodes|nodes expanded|node expansion|search nodes|explored nodes|traversed nodes",
}
TOOLS = {
    "MovingAI grid benchmarks": r"moving ?ai|movingai",
    "MAPF benchmarks": r"MAPF benchmark",
    "OMPL": r"\bOMPL\b",
    "Bench-MR": r"bench-?mr",
    "BARN": r"\bBARN\b",
    "Arena-Bench / arena-rosnav": r"arena-?(?:rosnav|bench)",
    "CommonRoad": r"commonroad",
    "nuPlan": r"nuplan",
    "CARLA": r"\bcarla\b",
    "Gazebo": r"gazebo",
    "ROS": r"\bROS\b|robot operating system",
    "MATLAB/Simulink": r"matlab|simulink",
    "CarSim/PreScan/TruckSim": r"carsim|prescan|trucksim",
    "Webots, CoppeliaSim, AirSim": r"webots|coppelia|v-?rep\b|airsim",
}
BASE = {
    "Compared with a traditional, original, or standard version": r"(?:compared (?:with|to)|than|over|against|relative to|outperform\w*)[^.]{0,40}(?:traditional|original|standard|conventional|basic|classical|classic)",
    "Any public benchmark or open driving simulator": r"moving ?ai|MAPF benchmark|\bOMPL\b|bench-?mr|\bBARN\b|arena-?(?:rosnav|bench)|commonroad|nuplan|\bcarla\b",
}
em = [dict(group=g, item=k, n=int(has(d, p).sum()), pct=round(100 * has(d, p).mean(), 1))
      for g, D in (("metric", METRICS), ("tool", TOOLS), ("indicator", BASE)) for k, p in D.items()]
em = pd.DataFrame(em)
em.to_csv(os.path.join(ROOT, "data", "evaluation_mentions.csv"), index=False)
print(dp.to_string(index=False))
print(em.to_string(index=False))
