"""
Fig. 6 -- Heat map: hybrid class x robot platform.

Counting rule: each cross-family hybrid study (include == "Y") adds +1 to (class, platform),
using its single primary platform. "Generic" = abstract point or configuration-space robot.

Run:  python figures/fig6_type_platform.py
"""
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from _common import load, save, class_order

PLAT = ["UGV", "UAV", "Car", "Marine", "Generic"]
LBL = {"UGV": "Ground robot (UGV)", "UAV": "Aerial (UAV)", "Car": "Autonomous car",
       "Marine": "Marine (USV/AUV)", "Generic": "Generic / abstract"}
df = load("hybrids")
df["cls2"] = df["cls"].where(df["cls"].str.count(r"\+") == 1, "Multi-family")
cls = class_order(df.loc[df["cls2"] != "Multi-family", "cls2"]) + ["Multi-family"]
M = pd.crosstab(df["cls2"], df["platform"]).reindex(index=cls, columns=PLAT, fill_value=0)
fig, ax = plt.subplots(figsize=(7.2, 0.38 * len(cls) + 1.8))
sns.heatmap(M, annot=True, fmt="d", cmap="Greens", linewidths=0.5, linecolor="white",
            cbar_kws={"label": "Number of studies"}, ax=ax, annot_kws={"size": 8})
ax.set_xticklabels([LBL[p] for p in PLAT], rotation=30, ha="right", fontsize=8)
ax.set_yticklabels(cls, rotation=0, fontsize=8); ax.set_xlabel(""); ax.set_ylabel("")
ax.set_title(f"Hybrid class vs. platform, mapped studies (n = {len(df):,})", fontsize=10)
plt.tight_layout(); save(fig, "fig6_type_platform"); print(M.to_string())
