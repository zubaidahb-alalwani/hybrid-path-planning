"""
Fig. 7 -- Static vs. dynamic evaluation environments.

Counting rule: each cross-family hybrid study (include == "Y") is counted once according to
`environment`: static (no moving obstacles in the evaluation), dynamic (moving obstacles),
both, or not yet coded ("?"). (a) overall shares; (b) by class group (Section IV subsections).

Run:  python figures/fig7_static_dynamic.py
"""
import pandas as pd
import matplotlib.pyplot as plt
from _common import load, save, GROUPS, GROUP_ORDER

CATS = ["static", "dynamic", "both", "?"]
LBL = {"static": "Static only", "dynamic": "Dynamic", "both": "Static and dynamic", "?": "Not reported"}
COL = {"static": "#6BAED6", "dynamic": "#E6550D", "both": "#FDAE6B", "?": "#D9D9D9"}
df = load("hybrids")
tot = df["environment"].value_counts().reindex(CATS, fill_value=0)
by = pd.crosstab(df["group"], df["environment"]).reindex(index=GROUP_ORDER, columns=CATS, fill_value=0)
fig, (a, b) = plt.subplots(1, 2, figsize=(9.5, 4.0), gridspec_kw={"width_ratios": [1, 1.6]})
a.pie(tot.values, labels=[f"{LBL[c]}\n(n = {v})" for c, v in tot.items()], colors=[COL[c] for c in CATS],
      startangle=90, counterclock=False, wedgeprops=dict(edgecolor="white"), textprops=dict(fontsize=8),
      autopct=lambda p: f"{p:.0f}%" if p > 0 else "", pctdistance=0.72)
a.set_title(f"(a) All mapped studies (n = {len(df):,})", fontsize=9)
left = pd.Series(0, index=by.index)
for c in CATS:
    b.barh([GROUPS[g] for g in by.index], by[c], left=left, color=COL[c], label=LBL[c], edgecolor="white")
    left += by[c]
b.invert_yaxis(); b.tick_params(labelsize=8); b.set_xlabel("Number of studies", fontsize=8)
b.set_title("(b) By class group", fontsize=9); b.legend(fontsize=7, frameon=False, loc="lower right")
b.spines[["top", "right"]].set_visible(False)
plt.tight_layout(); save(fig, "fig7_static_dynamic"); print(by.to_string()); print(tot.to_string())
