"""
Fig. 1 -- Flow diagram (PRISMA 2020 structure) for the systematic mapping study
"Hybrid Path Planning Algorithms for Mobile Robots and Autonomous Vehicles".

HOW TO USE
  1. Run the database searches in Table IV of the paper.
  2. Replace every `None` in COUNTS with the real number from your screening log
     (the same numbers go into the \\n... macros at the top of main.tex).
  3. Run:  python fig1_prisma.py   ->  fig1_prisma.pdf / fig1_prisma.png

Unfilled values are drawn as "n = ?" so the figure can never show invented numbers.
When every value is filled, the script checks that the flow is arithmetically consistent.
"""
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

# ----------------------------------------------------------------------------
# 1. COUNTS -- fill these from the screening log. Do NOT estimate.
# ----------------------------------------------------------------------------
COUNTS = {
    "db": {                      # records identified per database
        "IEEE Xplore": 9820,      # single 2015-2025 run, 7 Oct 2026
        "Scopus": 10236,          # 7 Oct 2026; ar + cp; English; 2015-2025
        "Scopus pair queries": 6585,  # 15 component-pair queries, 9 Oct 2026
        "ScienceDirect": 485,       # 9 Oct 2026; runs A 295 + B 171 + C 19
        "SpringerLink": 188,        # 9 Oct 2026; title search; articles 118 + conference papers 70
        "Google Scholar": 1000,     # supplementary; Publish or Perish, 9 Oct 2026; 1,000-record display limit
    },
    "duplicates": 8837,          # tools/merge_dedupe.py, 10 Oct 2026 (incl. 6 pairs judged by hand)
    "automation": 0,             # no automation tools used
    "other_removed": 9,          # 4 front matter, 4 retracted, 1 citation-only
    "excluded_ta": 14922,        # title/abstract screening by Z.B.A., 24 Oct 2026
    "not_retrieved": 3233,       # full text not obtainable (no institutional access), 26 Oct 2026;
                                 # these are classified from title, abstract and keywords
    "excluded_abs": {            # excluded after classification from title, abstract and keywords, by criterion
        "EC1": 739, "EC2": 51, "EC3": 368, "EC4": 195, "EC5": 5, "EC6": 0,
    },
    "excluded_ft": {             # full-text exclusions, keyed by eligibility criterion
        "EC1 single family / offline tuning": 341,
        "EC2 no quantitative evaluation": 16,
        "EC3 out of scope": 108,
        "EC4 insufficient detail": 25,
        "EC5 duplicate / superseded": 0,
        "EC6 not peer reviewed / not English": 3,
    },
}

# ----------------------------------------------------------------------------
# 2. Derived quantities (computed only when their inputs are known)
# ----------------------------------------------------------------------------
def _sum(vals):
    vals = list(vals)
    return None if any(v is None for v in vals) else sum(vals)

def _sub(a, *bs):
    if a is None or any(b is None for b in bs):
        return None
    return a - sum(bs)

C = COUNTS
total_db = _sum(C["db"].values())
screened = _sub(total_db, C["duplicates"], C["automation"], C["other_removed"])
sought = _sub(screened, C["excluded_ta"])
assessed = _sub(sought, C["not_retrieved"])
excluded_ft_total = _sum(C["excluded_ft"].values())
included_db = _sub(assessed, excluded_ft_total)
excluded_abs_total = _sum(C["excluded_abs"].values())
included_abs = _sub(C["not_retrieved"], excluded_abs_total)
included_total = None if included_db is None or included_abs is None else included_db + included_abs

for name, val in [("screened", screened), ("sought", sought), ("assessed", assessed),
                  ("included_db", included_db), ("included_abs", included_abs)]:
    if val is not None and val < 0:
        raise ValueError(f"Inconsistent PRISMA counts: '{name}' is negative ({val}).")

def n(v):
    return "n = ?" if v is None else f"n = {v:,}"

# ----------------------------------------------------------------------------
# 3. Drawing helpers
# ----------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.4, 9.6))
ax.set_xlim(0, 73)
ax.set_ylim(0, 100)
ax.axis("off")

BOX_KW = dict(boxstyle="round,pad=0.4,rounding_size=0.8", linewidth=1.2)

def box(x, y, w, h, text, fc="white", ec="black", fs=11.5, weight="normal"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, facecolor=fc, edgecolor=ec, **BOX_KW))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, fontweight=weight, linespacing=1.22)
    return dict(l=x, r=x + w, t=y + h, b=y, cx=x + w / 2, cy=y + h / 2)

def arrow(x0, y0, x1, y1):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle="-|>", lw=1.2, color="black"))

# Header bars
box(6, 93, 61, 5, "Identification of studies via databases",
    fc="#F2C94C", ec="#B8860B", fs=13, weight="bold")

# Phase side labels
for (y0, y1, label) in [(70, 92, "Identification"), (22, 69, "Screening"), (2, 16, "Included")]:
    ax.add_patch(FancyBboxPatch((0.3, y0), 4.2, y1 - y0, facecolor="#9DC3E6",
                                edgecolor="#2E75B6", **BOX_KW))
    ax.text(2.4, (y0 + y1) / 2, label, rotation=90, ha="center", va="center",
            fontsize=13, fontweight="bold")

# ---- Database column --------------------------------------------------------
db_lines = "\n".join(f"{k} ({n(v)})" for k, v in C["db"].items())
b_id = box(6, 70, 26, 22, f"Records identified from\ndatabases ({n(total_db)}):\n{db_lines}")
b_rm = box(36, 73, 31, 16,
           "Records removed before screening:\n"
           f"Duplicate records ({n(C['duplicates'])})\n"
           f"Marked ineligible by automation\ntools ({n(C['automation'])})\n"
           f"Removed for other reasons ({n(C['other_removed'])})")
arrow(b_id["r"], b_id["cy"], b_rm["l"], b_rm["cy"])

b_sc = box(6, 58, 26, 8, f"Records screened\n(title and abstract)\n({n(screened)})")
b_ex = box(36, 58, 31, 8, f"Records excluded\n({n(C['excluded_ta'])})")
arrow(b_id["cx"], b_id["b"], b_sc["cx"], b_sc["t"])
arrow(b_sc["r"], b_sc["cy"], b_ex["l"], b_ex["cy"])

b_so = box(6, 45, 26, 8, f"Reports sought for retrieval\n({n(sought)})")
abs_ex = "; ".join(f"{k} {v:,}" for k, v in list(C["excluded_abs"].items())[:3]) + "\n" + \
         "; ".join(f"{k} {v:,}" for k, v in list(C["excluded_abs"].items())[3:])
b_nr = box(36, 42.5, 31, 13, f"Full text not obtained ({n(C['not_retrieved'])}):\nclassified from title, abstract,\nkeywords; excluded ({n(excluded_abs_total)}):\n{abs_ex}", fs=11)
arrow(b_sc["cx"], b_sc["b"], b_so["cx"], b_so["t"])
arrow(b_so["r"], b_so["cy"], b_nr["l"], b_nr["cy"])

b_as = box(6, 30, 26, 9, f"Reports classified from\nfull text ({n(assessed)})")
ex_lines = "\n".join(f"{k} ({n(v)})" for k, v in C["excluded_ft"].items())
b_rx = box(36, 19, 31, 21, f"Reports excluded ({n(excluded_ft_total)}):\n{ex_lines}", fs=11)
arrow(b_so["cx"], b_so["b"], b_as["cx"], b_as["t"])
arrow(b_as["r"], b_as["cy"], b_rx["l"], b_as["cy"])

# ---- Included ----------------------------------------------------------------
b_in = box(6, 3, 61, 11,
           f"Studies in the map ({n(included_total)})\n"
           f"full-text set: {n(included_db)};  abstract set: {n(included_abs)}",
           fc="#E2F0D9", ec="#548235", fs=13, weight="bold")
arrow(b_as["cx"], b_as["b"], b_as["cx"], b_in["t"])


# abstract-set path: from the not-obtained box down the gap between columns to the map box
ax.plot([b_nr["r"], 71, 71], [b_nr["cy"], b_nr["cy"], b_in["cy"]], color="black", lw=1.2)
arrow(71, b_in["cy"], b_in["r"], b_in["cy"])

plt.tight_layout()
plt.savefig("fig1_prisma.pdf", bbox_inches="tight")
plt.savefig("fig1_prisma.png", dpi=300, bbox_inches="tight")

if included_total is None:
    print("NOTE: some PRISMA counts are still None and are shown as 'n = ?'. "
          "Fill COUNTS from the screening log before submission.")
else:
    print(f"PRISMA flow consistent. Studies included: {included_total}")
