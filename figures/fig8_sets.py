"""
Fig. 8 -- Representativeness: full-text set versus abstract set.
Counting rule: (a) share of studies in each set that contain each family (a study with k families
counts once for each); (b) share of studies in each set per platform. Shares are within each set.
Run:  python figures/fig8_sets.py
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from _common import load, save, FAMILIES, FAMILY_NAMES, fam_list, ROOT

df = load("hybrids")
sets = {"FT": "Full-text set", "Abs": "Abstract set"}
col = {"FT": "#2b6cb0", "Abs": "#9ec5e8"}
fam = pd.DataFrame({b: [df[df.basis == b]["families"].apply(lambda s: f in fam_list(s)).mean() * 100 for f in FAMILIES]
                    for b in sets}, index=FAMILIES)
PL = ["UGV", "UAV", "Car", "Marine", "Generic"]
pl = pd.DataFrame({b: df[df.basis == b]["platform"].value_counts(normalize=True).reindex(PL, fill_value=0) * 100 for b in sets})
fig, (a, b) = plt.subplots(1, 2, figsize=(9.6, 3.8))
w = 0.38
for ax, T, labels, title in ((a, fam, [f"{f}\n{FAMILY_NAMES[f]}" for f in FAMILIES], "(a) Studies containing each family (%)"),
                             (b, pl, PL, "(b) Platform (%)")):
    xs = np.arange(len(T))
    for i, s in enumerate(sets):
        bars = ax.bar(xs + (i - 0.5) * w, T[s], w, color=col[s], label=f"{sets[s]} (n = {(df.basis == s).sum():,})")
        for x, v in zip(xs + (i - 0.5) * w, T[s]):
            ax.text(x, v + 0.6, f"{v:.0f}", ha="center", va="bottom", fontsize=7)
    ax.set_xticks(xs); ax.set_xticklabels(labels, fontsize=7.5); ax.set_title(title, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False); ax.set_ylim(0, T.values.max() * 1.18)
a.legend(fontsize=7.5, frameon=False, loc="upper left")
plt.tight_layout(); save(fig, "fig8_sets")
pd.concat([fam.add_prefix("fam_"), pl.add_prefix("plat_")]).round(1).to_csv(os.path.join(ROOT, "data", "fig8_sets.csv"))
print(fam.round(1).to_string()); print(pl.round(1).to_string())
