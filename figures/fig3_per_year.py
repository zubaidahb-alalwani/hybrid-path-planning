"""
Fig. 3 -- Cross-family hybrid studies per publication year, stacked by class group.

Counting rule: every study with include == "Y" and a cross-family class code H[...]
(rules R1-R4) adds one count to (year, group), where the group is the lowest-indexed family
in the code (H[1+x], H[2+x], H[3+x], H[4+x] or H[5+6]); codes with three or more families
form the multi-family group. Class 0 and single-family studies are excluded. If
data/screening_counts_by_year.csv (columns year,records) exists, screened records per year
are overlaid on a secondary axis.

Run:  python figures/fig3_per_year.py
"""
import os
import pandas as pd
import matplotlib.pyplot as plt
from _common import load, save, GROUPS, GROUP_ORDER, ROOT

COLORS = {"D": "#1f77b4", "E": "#2ca02c", "F": "#d62728", "G": "#8c564b", "M": "#ff7f0e"}
df = load("hybrids")
years = list(range(2015, 2026))
tab = (df.groupby(["year", "group"]).size().unstack(fill_value=0)
         .reindex(index=years, columns=GROUP_ORDER, fill_value=0))
fig, ax = plt.subplots(figsize=(7.2, 4.2))
bottom = pd.Series(0, index=years)
for g in GROUP_ORDER:
    ax.bar(years, tab[g], bottom=bottom, color=COLORS[g], label=GROUPS[g], width=0.75, edgecolor="white", lw=0.5)
    bottom += tab[g]
for x, v in zip(years, bottom):
    if v:
        ax.text(x, v + bottom.max() * 0.01, str(int(v)), ha="center", va="bottom", fontsize=8)
ax.set_xticks(years); ax.set_xlabel("Publication year"); ax.set_ylabel("Number of mapped hybrid studies")
ax.set_ylim(0, bottom.max() * 1.1); ax.spines[["top", "right"]].set_visible(False)
scr = os.path.join(ROOT, "data", "screening_counts_by_year.csv")
if os.path.exists(scr):
    s = pd.read_csv(scr).set_index("year").reindex(years)
    ax2 = ax.twinx(); ax2.plot(years, s["records"], "k--o", ms=3, lw=1, label="Screened records")
    ax2.set_ylabel("Screened records"); ax2.legend(loc="upper right", fontsize=7, frameon=False)
ax.legend(fontsize=7, frameon=False, loc="upper left", ncol=2)
ax.set_title(f"Mapped hybrid studies per year (n = {len(df):,})", fontsize=10)
plt.tight_layout(); save(fig, "fig3_per_year")
print(tab.assign(total=tab.sum(axis=1)).to_string())
