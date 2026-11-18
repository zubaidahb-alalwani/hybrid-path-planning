"""
Fig. 5 -- Heat maps: hybrid class x integration strategy and x planning level (full-text set).
Counting rule: each mapped study classified from full text (basis == "FT") adds +1 to
(class, integration) and to (class, level). Integration and level are not reported for the
abstract set, because abstracts rarely state how components are combined.
Classes with three or more families are pooled as "Multi-family".
Run:  python figures/fig5_type_metric.py
(The file name is kept for compatibility; the figure no longer shows metrics, which were not coded.)
"""
import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from _common import load, save, class_order, ROOT

df = load("hybrids", basis="FT")
df["cls2"] = df["cls"].where(df["cls"].str.count(r"\+") == 1, "Multi-family")
two = class_order(df.loc[df["cls2"] != "Multi-family", "cls2"])
rows = two + ["Multi-family"]
I = pd.crosstab(df["cls2"], df["integration"]).reindex(index=rows, columns=["S", "E", "P", "?"], fill_value=0)
L = pd.crosstab(df["cls2"], df["level"]).reindex(index=rows, columns=["G", "L", "G-L", "?"], fill_value=0)
fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.6, 0.36 * len(rows) + 1.9), sharey=True)
sns.heatmap(I, annot=True, fmt="d", cmap="Blues", cbar=False, linewidths=0.5, linecolor="white", ax=a1, annot_kws={"size": 8})
a1.set_xticklabels(["Sequential", "Embedded", "Parallel", "Not reported"], rotation=30, ha="right", fontsize=8)
a1.set_yticklabels(rows, rotation=0, fontsize=8); a1.set_title("(a) Integration strategy", fontsize=9); a1.set_xlabel(""); a1.set_ylabel("")
sns.heatmap(L, annot=True, fmt="d", cmap="Purples", cbar=False, linewidths=0.5, linecolor="white", ax=a2, annot_kws={"size": 8})
a2.set_xticklabels(["Global", "Local", "Layered", "Not reported"], rotation=30, ha="right", fontsize=8)
a2.set_title("(b) Planning level", fontsize=9); a2.set_xlabel(""); a2.set_ylabel("")
fig.suptitle(f"Hybrid class vs. integration and level, full-text set (n = {len(df):,})", fontsize=10)
plt.tight_layout(); save(fig, "fig5_type_metric")
pd.concat([I.add_prefix("int_"), L.add_prefix("lev_")], axis=1).to_csv(os.path.join(ROOT, "data", "fig5_matrix.csv"))
print(I.to_string()); print(L.to_string())
