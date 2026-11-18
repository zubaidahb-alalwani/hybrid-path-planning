"""
Shared loader for the figure/table scripts.

Class codes follow rules R1-R4 (Section IV-A):
  * two or more DIFFERENT core families  -> H[a+b(+c)]   (cross-family hybrid)
  * one family listed twice (e.g. F5;F5) -> C0           (intra-family, Class 0)
  * one family only                      -> single       (not a hybrid)
  * any uncoded family ("?")             -> ?
Groups mirror the subsections of Section IV:
  IV-D  H[1+x]   IV-E  H[2+x]   IV-F  H[3+x]   IV-G  H[4+x], H[5+6]   IV-H  multi-family / Class 0
"""
import os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FAMILIES = ["F1", "F2", "F3", "F4", "F5", "F6"]
FAMILY_NAMES = {"F1": "Graph search", "F2": "Sampling", "F3": "Reactive", "F4": "Optimization",
                "F5": "Metaheuristic", "F6": "Learning/AI"}
GROUPS = {"D": "H[1+x] graph search", "E": "H[2+x] sampling", "F": "H[3+x] reactive",
          "G": "H[4+x], H[5+6]", "M": "Multi-family"}
GROUP_ORDER = ["D", "E", "F", "G", "M"]

def fam_list(s):
    return [f.strip() for f in str(s).split(";")]

def class_code(fams):
    if "?" in fams:
        return "?"
    d = sorted(set(fams), key=FAMILIES.index)
    if len(d) == 1:
        return "C0" if len(fams) >= 2 else "single"
    return "H[" + "+".join(x[1:] for x in d) + "]"

def group_of(code):
    if not code.startswith("H["):
        return code
    nums = code[2:-1].split("+")
    if len(nums) >= 3:
        return "M"
    return {"1": "D", "2": "E", "3": "F", "4": "G", "5": "G"}[nums[0]]

def load(which="hybrids", source="mapped", basis=None):
    """which = 'hybrids' (cross-family, include == Y), 'all_included' (incl. Class 0), or 'all'.
    source = 'mapped' (data/mapped_studies.csv, the studies of the systematic map; used by Figs. 3-8)
             or 'representative' (data/included_studies.csv, the representative studies of Section IV;
             used by the comparison tables). basis = None (all), 'FT' or 'Abs' (mapped source only)."""
    fname = "mapped_studies.csv" if source == "mapped" else "included_studies.csv"
    df = pd.read_csv(os.path.join(ROOT, "data", fname), keep_default_na=False)
    if basis is not None:
        df = df[df["basis"] == basis].copy()
    df["cls"] = df["families"].apply(lambda s: class_code(fam_list(s)))
    df["group"] = df["cls"].apply(group_of)
    if which == "all":
        return df
    df = df[df["include"] == "Y"].copy()
    if which == "hybrids":
        df = df[df["cls"].str.startswith("H[")]
    return df

def class_order(codes):
    def key(c):
        return (len(c), [int(x) for x in c[2:-1].split("+")])
    return sorted(set(codes), key=key)

def save(fig, name):
    fig.savefig(os.path.join(HERE, name + ".pdf"), bbox_inches="tight")
    fig.savefig(os.path.join(HERE, name + ".png"), dpi=300, bbox_inches="tight")
