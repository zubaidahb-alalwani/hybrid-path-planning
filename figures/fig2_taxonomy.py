"""
Figure 1 -- Taxonomy of path-planning method families and hybrid classes (manuscript Sections 3.1 and 3.2).

Left: the six core families F1-F6 derived from the nine-review crosswalk (Table VIII) plus the
auxiliary family A (interpolating curves). Right: the hybrid classes:
the 15 two-family classes H[a+b] arranged as an upper-triangular grid, and multi-family classes.
The figure is definitional (it shows the classification scheme, not frequencies); the number of
mapped studies per pair is shown in the co-occurrence figure (fig4_cooccurrence.py).

Run:  python figures/fig2_taxonomy.py
"""
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from _common import save

FAM = [("F1", "Graph search", "Dijkstra, A*, D* Lite, JPS,\nTheta*, Hybrid A*, lattice"),
       ("F2", "Sampling", "PRM, RRT, RRT*,\nInformed RRT*, BIT*, FMT*"),
       ("F3", "Reactive", "APF, DWA, VFH,\nVO, Bug, TEB"),
       ("F4", "Optimization", "MPC, CHOMP, TrajOpt,\nMILP, optimal control"),
       ("F5", "Metaheuristic", "GA, PSO, ACO,\nGWO, ABC, DE"),
       ("F6", "Learning / AI", "DRL, imitation, neural\nplanners, fuzzy logic")]
COL = {"F1": "#1f77b4", "F2": "#2ca02c", "F3": "#d62728", "F4": "#9467bd", "F5": "#8c564b", "F6": "#ff7f0e"}
TINY = {"F1": "Graph", "F2": "Sampling", "F3": "Reactive", "F4": "Optim.", "F5": "Metaheur.", "F6": "Learning"}
SHORT = {"F1": "Graph", "F2": "Sampling", "F3": "Reactive", "F4": "Optimization", "F5": "Metaheuristic", "F6": "Learning"}

fig, ax = plt.subplots(figsize=(12, 8.2))
ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")
INK, INK2, HUB = "#1f1f1f", "#52514e", "#8a5a00"


def box(x, y, w, h, fc, ec, lw=1.2, ls="-", r=0.8):
    ax.add_patch(FancyBboxPatch((x, y), w, h, facecolor=fc, edgecolor=ec, linestyle=ls, linewidth=lw,
                                boxstyle=f"round,pad=0.25,rounding_size={r}"))


# ---- left: root and the families ------------------------------------------------------------
box(0.6, 45, 8.4, 10, "#ECEBE7", "#7a7974")
ax.text(4.8, 50, "Path\nplanning", ha="center", va="center", fontsize=15, fontweight="bold", color=INK)
ax.text(24, 97, "Core families (Section 3.1)", ha="center", fontsize=15, fontweight="bold", color=INK)
YC = [87, 75.2, 63.4, 51.6, 39.8, 28]
for (k, n, ex), y in zip(FAM, YC):
    box(12.6, y - 5.1, 26.8, 10.2, "#FFFFFF", COL[k], lw=2)
    ax.text(13.6, y + 2.6, f"{k}  {n}", ha="left", va="center", fontsize=14, fontweight="bold", color=COL[k])
    ax.text(13.6, y - 1.6, ex, ha="left", va="center", fontsize=12, color=INK2, linespacing=1.15)
    ax.plot([9.2, 12.8], [50, y], color="#b0afa9", lw=0.9, zorder=0)
ya = 16.2
box(12.6, ya - 5.1, 26.8, 10.2, "#F7F7F5", "#8f8e88", ls="--")
ax.text(13.6, ya + 2.6, "A  Curves (auxiliary)", ha="left", va="center", fontsize=14, fontweight="bold", color=INK2)
ax.text(13.6, ya - 1.6, "Bezier, B-spline, clothoid,\npolynomial fitting", ha="left", va="center", fontsize=12, color=INK2, linespacing=1.15)
ax.plot([9.2, 12.8], [50, ya], color="#b0afa9", lw=0.9, ls="--", zorder=0)
ax.text(26, 3.5, "Smoothing alone is not a family (rule R3)", ha="center", fontsize=12, style="italic", color=INK2)

# ---- right: hybrid classes ---------------------------------------------------------------------
ax.text(72, 98, "Hybrid classes (Section 3.2)", ha="center", fontsize=15, fontweight="bold", color=HUB)
x0, ytop, cw, ch = 48.5, 89, 10.3, 12.8           # grid: rows a = F1..F5, cols b = F2..F6
ax.plot([39.6, 41.5], [50, 50], color=HUB, lw=1.1, zorder=0)
ax.plot([41.5, 41.5], [13, 50], color=HUB, lw=1.1, zorder=0)
ax.plot([41.5, 41.5, 49.6], [50, 40, 40], color=HUB, lw=1.1, zorder=0)   # -> two-family classes
ax.plot([41.5, 43.4], [13, 13], color=HUB, lw=1.1, zorder=0)
ax.text(58.5, 40, "Two-family\nclasses H[a+b]\n(15)", ha="center", va="center", fontsize=13, color=HUB, fontweight="bold")
for bi, b in enumerate(["F2", "F3", "F4", "F5", "F6"]):
    ax.text(x0 + bi * cw + cw / 2, ytop + 1.0, f"{b}\n{SHORT[b]}", ha="center", va="bottom", fontsize=11.5, color=COL[b], fontweight="bold")
for ai, a in enumerate(["F1", "F2", "F3", "F4", "F5"]):
    yy = ytop - (ai + 1) * ch
    for bi, b in enumerate(["F2", "F3", "F4", "F5", "F6"]):
        if bi < ai:
            continue
        xx = x0 + bi * cw
        box(xx + 0.45, yy + 0.55, cw - 0.9, ch - 1.1, "#FFFFFF", COL[a], lw=1.6)
        ax.add_patch(plt.Rectangle((xx + 0.55, yy + ch - 1.75), cw - 1.1, 0.9, color=COL[b], lw=0))
        ax.text(xx + cw / 2, yy + ch / 2 + 1.6, f"H[{a[1]}+{b[1]}]", ha="center", va="center", fontsize=14, fontweight="bold", color=INK)
        ax.text(xx + cw / 2, yy + ch / 2 - 2.6, f"{TINY[a]} +\n{TINY[b]}", ha="center", va="center", fontsize=11, color=INK2, linespacing=1.05)
    # row label sits in the empty lower-left triangle, next to the row's first cell
    ax.text(x0 + ai * cw - 0.4, yy + ch / 2, f"{a} {SHORT[a]}", ha="right", va="center", fontsize=11.5, color=COL[a], fontweight="bold")
# multi-family, in the free lower-left area of the grid
box(42.6, 2.5, 22, 17, "#FFF8E6", HUB, lw=1.4)
ax.text(53.6, 15.6, "Multi-family H[a+b+c]", ha="center", fontsize=13, fontweight="bold", color=INK)
ax.text(53.6, 8.6, "three or more families,\ne.g., H[1+3+6], H[1+3+5],\nH[1+2+3]", ha="center", va="center", fontsize=12, color=INK2)
ax.text(67, 11, "Each class is also coded by integration\n(S sequential, E embedded, P parallel),\nplanning level (G global, L local,\nG-L layered) and environment,\ne.g., H[1+3]-S | G-L | dynamic.\n"
        "Cell border: first family;\ntop strip: second family.",
        ha="left", va="center", fontsize=11.5, style="italic", color=INK2)
plt.tight_layout()
save(fig, "fig2_taxonomy")
print("Saved fig2_taxonomy")
