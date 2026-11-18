"""
Fig. 4 -- Family co-occurrence heat map (F1-F6).

Counting rule (per study with include == "Y" and no uncoded family):
  * off-diagonal (a, b): +1 if the study combines families a and b (a multi-family study
    contributes to every pair it contains);
  * diagonal (a, a): intra-family combinations; empty, because they were excluded under EC1.
Each study counts at most once per cell. The figure shows the 15 off-diagonal cells (lower triangle),
each labelled with its class code; tick labels give the number of studies containing each family.

Run:  python figures/fig4_cooccurrence.py
"""
import os
from itertools import combinations
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from _common import load, save, FAMILIES, FAMILY_NAMES, fam_list, ROOT

df = load("all_included")
M = pd.DataFrame(0, index=FAMILIES, columns=FAMILIES)
used = 0
for _, r in df.iterrows():
    f = fam_list(r["families"])
    if "?" in f:
        continue
    used += 1
    for x in set(f):
        if f.count(x) >= 2:
            M.loc[x, x] += 1
    for a, b in combinations(sorted(set(f), key=FAMILIES.index), 2):
        M.loc[b, a] += 1; M.loc[a, b] += 1
# ---- plot: the 15 family pairs (lower triangle, no diagonal), single-hue sequential ramp ----------
from matplotlib.colors import LinearSegmentedColormap
BLUES = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
cmap = LinearSegmentedColormap.from_list("seq_blue", BLUES)
tot = {k: int(df["families"].apply(lambda s, k=k: k in fam_list(s)).sum()) for k in FAMILIES}
rows, cols = FAMILIES[1:], FAMILIES[:-1]
P = M.loc[rows, cols].astype(float)
for i, r in enumerate(rows):
    for j, c in enumerate(cols):
        if j > i:
            P.loc[r, c] = np.nan
vmax = np.nanmax(P.values)
two = load("hybrids")["cls"].value_counts().to_dict()   # studies of the two-family class itself
fig, ax = plt.subplots(figsize=(5.6, 4.4))
ax.imshow(np.ma.masked_invalid(P.values), cmap=cmap, vmin=0, vmax=vmax)
for i in range(len(rows)):
    for j in range(len(cols)):
        v = P.values[i, j]
        if np.isnan(v):
            continue
        ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, ec="white", lw=2))
        dark = v > 0.42 * vmax
        ax.text(j, i - 0.08, f"{int(v)}", ha="center", va="center", fontsize=10, fontweight="bold",
                color="white" if dark else "#1f1f1f")
        code = f"H[{FAMILIES.index(cols[j]) + 1}+{FAMILIES.index(rows[i]) + 1}]"
        ax.text(j, i + 0.25, f"{code}: {two[code]}", ha="center",
                va="center", fontsize=6.5, color="white" if dark else "#1f1f1f")
ax.set_xticks(range(len(cols)))
ax.set_xticklabels([f"{k}\n{FAMILY_NAMES[k]}\n({tot[k]:,})" for k in cols], fontsize=7.5)
ax.set_yticks(range(len(rows)))
ax.set_yticklabels([f"{k} {FAMILY_NAMES[k]} ({tot[k]:,})" for k in rows], fontsize=7.5)
ax.tick_params(length=0)
for sp in ax.spines.values():
    sp.set_visible(False)
ax.set_xlim(-0.5, len(cols) - 0.5); ax.set_ylim(len(rows) - 0.5, -0.5)
sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, vmax)); sm.set_array([])
cb = fig.colorbar(sm, ax=ax, fraction=0.04, pad=0.02)
cb.set_label("Mapped studies containing the pair", fontsize=8); cb.ax.tick_params(labelsize=7); cb.outline.set_visible(False)
ax.text(len(cols) - 0.5, -0.45, f"n = {used:,} mapped studies\nLarge number: studies containing the pair\nSmall: two-family class only\n(in parentheses: studies with the family)",
        ha="right", va="top", fontsize=7, color="#555555")
plt.tight_layout(); save(fig, "fig4_cooccurrence")
mask = np.triu(np.ones_like(M, dtype=bool), k=1)
M.to_csv(os.path.join(ROOT, "data", "fig4_cooccurrence_matrix.csv"))
print(f"Studies used: {used}"); print(M.where(~mask).fillna("").to_string())
