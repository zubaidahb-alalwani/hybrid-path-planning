#!/usr/bin/env python3
"""
merge_dedupe.py -- merge the database exports of the systematic review
"Hybrid Path Planning Algorithms for Mobile Robots and Autonomous Vehicles"
and remove duplicate records, keeping a log of every record removed.

INPUT (exports exactly as downloaded):
  --ieee      IEEE Xplore CSV (one merged file, or several files)
  --scopus    Scopus CSV
  --pairs     Scopus CSVs of the 15 supplementary component-pair queries (optional)
  --sd        ScienceDirect RIS files (runs A, B, C; any number of files)
  --springer  SpringerLink CSV ("Download results (.csv)")
  --gs        Google Scholar CSV from Publish or Perish
  --out       output folder

OUTPUT (in --out):
  records_for_screening.csv   one row per unique record, ready for title/abstract screening
  records_for_screening.ris   the same records as RIS, for import into Rayyan, Zotero, EndNote
  removal_log.csv             every record removed, with the reason and the record it duplicates
  title_based_merges.csv      every duplicate matched on title (no shared DOI), lowest similarity first
  possible_duplicates.csv     pairs with the same title, year and first author but different DOIs
                              (kept as separate records; check them by hand during screening)
  prisma_counts.txt           the numbers for the identification boxes of the PRISMA flow diagram

RULES
  1. "Removed for other reasons": front matter (cover, table of contents, index ...),
     Google Scholar citation-only records, and retracted records.
  2. Two records are duplicates if
       a. their DOIs are identical, or
       b. their normalised titles match (similarity >= 95/100), their years differ by
          at most one, their first-author surnames agree (when both are known), and
          they do not carry two different DOIs.
     Title matches between records with different DOIs are NOT merged; they are
     listed in possible_duplicates.csv (e.g. a paper presented at two conferences).
  3. From each group of duplicates one record is kept, chosen in this order:
     Scopus, IEEE Xplore, ScienceDirect, SpringerLink, Google Scholar. Its abstract,
     DOI and keywords are filled from the other members when missing, and the
     "sources" column lists every database that found it.

USAGE
  pip install pandas rapidfuzz
  python merge_dedupe.py --ieee ieee.csv --scopus scopus.csv \
      --sd sd_A_01.ris sd_A_02.ris sd_A_03.ris sd_B_01.ris sd_B_02.ris sd_C.ris \
      --springer springerlink.csv --gs google_scholar_1000.csv --out merged
"""
import argparse, html, os, re, sys, unicodedata
from collections import defaultdict

import pandas as pd

try:
    from rapidfuzz import fuzz
    from rapidfuzz.process import cdist
except ImportError:  # pragma: no cover
    sys.exit("Please install rapidfuzz first:  pip install rapidfuzz")

SOURCE_ORDER = ["Scopus", "Scopus pair queries", "IEEE Xplore", "ScienceDirect", "SpringerLink", "Google Scholar"]
TITLE_THRESHOLD = 95

FRONT_MATTER = re.compile(
    r"^\s*(\[?front cover\]?|\[?back cover\]?|table of contents|contents|author index|index|"
    r"title page|copyright( page| notice)?|committees?|organizing committee|welcome message.*|"
    r"message from .*|preface|foreword|editorial board|front matter|back matter|\[.*\])\s*$",
    re.I)

# concept blocks of the search (checked in title, abstract and keywords, to help screening)
BLOCKS = {
    "C1": r"\bhybrid|\bcombin\w*|\bfusion\b|\bintegrat\w*|\bhierarchical\b|\btwo layer\b|\btwo level\b",
    "C2": r"path planning|motion planning|trajectory planning|trajectory generation",
    "C3": r"mobile robot|autonomous vehicle|self driving|automated driving|\bua?vs?\b|unmanned aerial|"
          r"\bugvs?\b|\bauvs?\b|unmanned surface|unmanned underwater|unmanned ground|underwater vehicle|"
          r"surface vehicle|\bmanipulator",
}


# ----------------------------------------------------------------------------- helpers
def ascii_lower(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return s.lower()


def norm_title(t):
    t = ascii_lower(t).replace("…", " ").replace("...", " ")
    t = re.sub(r"<[^>]+>", " ", t)              # html tags
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def norm_doi(d):
    d = str(d or "").strip().lower()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    d = d.replace("doi:", "").strip()
    return d if d.startswith("10.") else ""


def to_year(y):
    m = re.search(r"(19|20)\d{2}", str(y or ""))
    return int(m.group(0)) if m else None


def surname(name, style):
    """first-author surname from the author string of each database"""
    name = str(name or "").strip()
    if not name:
        return ""
    if style == "ieee":        # "P. Yu; D. V. Dimarogonas"
        first = name.split(";")[0].strip()
        s = first.split()[-1] if first.split() else ""
    elif style == "scopus":    # "Wei C.; He L."
        first = name.split(";")[0].strip()
        s = first.split()[0] if first.split() else ""
    elif style == "ris":       # "Kumar, Sandeep A."
        s = name.split(";")[0].split(",")[0]
    elif style == "gs":        # "S Kumar, J Vanualailai"
        first = name.split(",")[0].strip()
        s = first.split()[-1] if first.split() else ""
    else:
        return ""
    return re.sub(r"[^a-z]", "", ascii_lower(s))


def read_csv(path):
    return pd.read_csv(path, dtype=str, encoding="utf-8-sig", keep_default_na=False)


def parse_ris(path):
    recs, cur, last = [], {}, None
    with open(path, encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.rstrip("\n")
            m = re.match(r"^([A-Z][A-Z0-9])  -\s?(.*)$", line)
            if m:
                tag, val = m.groups()
                if tag == "ER":
                    recs.append(cur); cur, last = {}, None
                    continue
                if tag in ("AU", "KW") and tag in cur:
                    cur[tag] += "; " + val
                elif tag in cur:
                    cur[tag] += " " + val
                else:
                    cur[tag] = val
                last = tag
            elif line.strip() and last:
                cur[last] += " " + line.strip()   # continuation line (abstract paragraphs)
    return recs


# ----------------------------------------------------------------------------- loaders
def rec(source, file, title, authors, year, venue, doi, abstract, keywords, doc_type, url,
        first_author, gs_rank=""):
    title = re.sub(r"\s+", " ", html.unescape(str(title))).strip()
    return dict(source=source, file=os.path.basename(file), title=title,
                authors=str(authors).strip(), year=to_year(year), venue=str(venue).strip(),
                doi=norm_doi(doi), abstract=str(abstract).strip(), keywords=str(keywords).strip(),
                doc_type=str(doc_type).strip(), url=str(url).strip(), first_author=first_author,
                gs_rank=str(gs_rank))


def load_ieee(paths):
    out = []
    for p in paths:
        for _, r in read_csv(p).iterrows():
            kw = "; ".join(x for x in (r.get("Author Keywords", ""), r.get("IEEE Terms", "")) if x)
            out.append(rec("IEEE Xplore", p, r["Document Title"], r["Authors"], r["Publication Year"],
                           r["Publication Title"], r["DOI"], r["Abstract"], kw,
                           r.get("Document Identifier", ""), r.get("PDF Link", ""),
                           surname(r["Authors"], "ieee")))
    return out


def load_scopus(paths, source="Scopus"):
    out = []
    for p in paths:
        for _, r in read_csv(p).iterrows():
            kw = "; ".join(x for x in (r.get("Author Keywords", ""), r.get("Index Keywords", "")) if x)
            out.append(rec(source, p, r["Title"], r["Authors"], r["Year"], r["Source title"],
                           r["DOI"], r["Abstract"], kw, r.get("Document Type", ""), r.get("Link", ""),
                           surname(r["Authors"], "scopus")))
    return out


def load_sd(paths):
    out = []
    for p in paths:
        for r in parse_ris(p):
            out.append(rec("ScienceDirect", p, r.get("T1", r.get("TI", "")), r.get("AU", ""),
                           r.get("PY", r.get("DA", "")), r.get("JO", r.get("T2", "")), r.get("DO", ""),
                           r.get("AB", ""), r.get("KW", ""), r.get("TY", ""), r.get("UR", ""),
                           surname(r.get("AU", ""), "ris")))
    return out


def load_springer(paths):
    out = []
    for p in paths:
        for _, r in read_csv(p).iterrows():
            # the SpringerLink CSV joins author names without separators, so no first author
            out.append(rec("SpringerLink", p, r["Item Title"], r["Authors"], r["Publication Year"],
                           r["Publication Title"], r["Item DOI"], "", "", r["Content Type"], r["URL"], ""))
    return out


def load_gs(paths):
    out = []
    for p in paths:
        for _, r in read_csv(p).iterrows():
            out.append(rec("Google Scholar", p, r["Title"], r["Authors"], r["Year"], r["Source"],
                           r.get("DOI", ""), r.get("Abstract", ""), "", r.get("Type", ""),
                           r.get("ArticleURL", ""), surname(r["Authors"], "gs"), r.get("GSRank", "")))
    return out


# ----------------------------------------------------------------------------- union-find
class DSU:
    def __init__(self, n):
        self.p = list(range(n))
        self.dois = [set() for _ in range(n)]

    def find(self, a):
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        a, b = self.find(a), self.find(b)
        if a != b:
            self.p[b] = a
            self.dois[a] |= self.dois[b]
        return a


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ieee", nargs="*", default=[])
    ap.add_argument("--scopus", nargs="*", default=[])
    ap.add_argument("--pairs", nargs="*", default=[],
                    help="Scopus component-pair query exports (pair_F1F2.csv ... pair_F5F6.csv)")
    ap.add_argument("--sd", nargs="*", default=[])
    ap.add_argument("--springer", nargs="*", default=[])
    ap.add_argument("--gs", nargs="*", default=[])
    ap.add_argument("--manual", default="",
                    help="CSV of record pairs judged by hand (columns doi_1, doi_2, decision, reason); "
                         "pairs with decision 'duplicate' are merged")
    ap.add_argument("--out", default="merged")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    records = (load_scopus(a.scopus) + load_scopus(a.pairs, "Scopus pair queries")
               + load_ieee(a.ieee) + load_sd(a.sd)
               + load_springer(a.springer) + load_gs(a.gs))
    df = pd.DataFrame(records)
    df["rid"] = range(len(df))
    df["tnorm"] = df["title"].map(norm_title)
    identified = df.groupby("source").size().reindex(SOURCE_ORDER).dropna().astype(int)
    print("Records identified:", identified.to_dict(), "total", len(df))

    # ---- 1. removed for other reasons
    reason = pd.Series("", index=df.index)
    reason[df["title"].str.match(FRONT_MATTER) | (df["tnorm"] == "")] = "front matter / no title"
    gs = df["source"] == "Google Scholar"
    reason[gs & df["doc_type"].str.upper().eq("CITATION")] = "Google Scholar citation-only record"
    retr = df["doc_type"].str.lower().str.contains("retract") | df["title"].str.match(r"(?i)^\s*retract(ed|ion)")
    reason[retr] = "retracted"
    other = df[reason != ""].copy()
    other["reason"] = reason[reason != ""]
    work = df[reason == ""].reset_index(drop=True)

    # ---- 2. duplicates
    n = len(work)
    dsu = DSU(n)
    for i, d in enumerate(work["doi"]):
        if d:
            dsu.dois[i].add(d)
    # 2a. identical DOI
    by_doi = defaultdict(list)
    for i, d in enumerate(work["doi"]):
        if d:
            by_doi[d].append(i)
    for idx in by_doi.values():
        for j in idx[1:]:
            dsu.union(idx[0], j)
    # 2b. title + year (+/-1) + first author, unless two different DOIs
    possible = []
    years = work["year"].fillna(0).astype(int).values
    titles = work["tnorm"].tolist()
    orig_titles = work["title"].tolist()
    fa = work["first_author"].tolist()
    order = sorted(set(years))
    for y in order:
        A = [i for i in range(n) if years[i] == y]
        B = [i for i in range(n) if years[i] in (y, y + 1)]
        if not A or not B:
            continue
        Bt = [titles[j] for j in B]
        hits = []
        for k in range(0, len(A), 1000):          # chunks keep memory use small
            chunk = A[k:k + 1000]
            S = cdist([titles[i] for i in chunk], Bt, scorer=fuzz.ratio,
                      score_cutoff=TITLE_THRESHOLD, workers=-1, dtype="uint8")
            hits += [(chunk[ai], B[bj]) for ai, bj in zip(*S.nonzero())]
        for i, j in hits:
            if i >= j and years[j] == y:
                continue                      # each same-year pair once
            if fa[i] and fa[j] and fa[i] != fa[j]:
                continue                      # different first authors: different papers
            ri, rj = dsu.find(i), dsu.find(j)
            if ri == rj:
                continue
            di, dj = dsu.dois[ri], dsu.dois[rj]
            if di and dj and not (di & dj):
                possible.append((i, j))       # same title, different DOIs: keep both, flag
                continue
            dsu.union(ri, rj)

    # 2c. pairs judged duplicates by hand (from possible_duplicates.csv)
    manual_merged, manual_pairs = 0, set()
    if a.manual:
        man = pd.read_csv(a.manual, dtype=str, keep_default_na=False)
        idx_of = defaultdict(list)
        for i, d in enumerate(work["doi"]):
            if d:
                idx_of[d].append(i)
        for _, m in man.iterrows():
            if m["decision"].strip().lower() != "duplicate":
                continue
            i1, i2 = idx_of.get(norm_doi(m["doi_1"])), idx_of.get(norm_doi(m["doi_2"]))
            if not i1 or not i2:
                print("manual pair not found:", m["doi_1"], m["doi_2"])
                continue
            manual_pairs.add(frozenset((norm_doi(m["doi_1"]), norm_doi(m["doi_2"]))))
            if dsu.find(i1[0]) != dsu.find(i2[0]):
                dsu.union(i1[0], i2[0]); manual_merged += 1

    work["cluster"] = [dsu.find(i) for i in range(n)]
    rank = {s: k for k, s in enumerate(SOURCE_ORDER)}
    work["src_rank"] = work["source"].map(rank)
    work["abs_len"] = work["abstract"].str.len()
    work = work.sort_values(["cluster", "src_rank", "abs_len"], ascending=[True, True, False])

    kept_rows, log_rows = [], []
    for cid, g in work.groupby("cluster", sort=False):
        keep = g.iloc[0].copy()
        others = g.iloc[1:]
        # fill missing fields from the other members
        non_gs = g[g["source"] != "Google Scholar"]
        pool = non_gs if len(non_gs) else g
        if pool["abs_len"].max() > keep["abs_len"]:
            keep["abstract"] = pool.loc[pool["abs_len"].idxmax(), "abstract"]
        if not keep["doi"]:
            dois = [d for d in g["doi"] if d]
            keep["doi"] = dois[0] if dois else ""
        if not keep["keywords"]:
            kws = [k for k in g["keywords"] if k]
            keep["keywords"] = kws[0] if kws else ""
        srcs = [s for s in SOURCE_ORDER if s in set(g["source"])]
        keep["sources"] = "; ".join(srcs)
        keep["n_sources"] = len(srcs)
        ranks = [r for r in g["gs_rank"] if r]
        keep["gs_rank"] = ranks[0] if ranks else ""
        kept_rows.append(keep)
        for _, o in others.iterrows():
            by_doi = bool(o["doi"]) and o["doi"] in set(g.loc[g.index != o.name, "doi"])
            by_title = fuzz.ratio(o["tnorm"], keep["tnorm"]) >= TITLE_THRESHOLD
            log_rows.append(dict(source=o["source"], file=o["file"], title=o["title"], year=o["year"],
                                 doi=o["doi"],
                                 matched_by="DOI" if by_doi else
                                 ("manual" if frozenset((o["doi"], keep["doi"])) in manual_pairs
                                  else ("title" if by_title else "manual")),
                                 title_similarity=round(fuzz.ratio(o["tnorm"], keep["tnorm"])),
                                 reason="duplicate (same source)" if o["source"] == keep["source"]
                                 else "duplicate (other source)",
                                 kept_record=f"R{int(keep['rid']):05d}", kept_source=keep["source"]))

    kept = pd.DataFrame(kept_rows)
    kept["record_id"] = kept["rid"].map(lambda r: f"R{int(r):05d}")
    txt = (kept["title"] + " " + kept["abstract"] + " " + kept["keywords"]).map(ascii_lower).str.replace(r"[-_/]", " ", regex=True)
    found = {b: txt.str.contains(p, regex=True) for b, p in BLOCKS.items()}
    kept["blocks_found"] = [" ".join(b for b in BLOCKS if found[b].iloc[k]) for k in range(len(kept))]
    kept["all_blocks"] = ["Y" if len(x.split()) == 3 else "N" for x in kept["blocks_found"]]
    # possible duplicates (same title, different DOIs) -> flag on both kept records
    cluster_keep = {c: f"R{int(r):05d}" for c, r in zip(kept["cluster"], kept["rid"])}
    flags = defaultdict(set)
    pd_rows, seen_pairs = [], set()
    for i, j in possible:
        ci, cj = cluster_keep[dsu.find(i)], cluster_keep[dsu.find(j)]
        if ci == cj or frozenset((ci, cj)) in seen_pairs:
            continue
        seen_pairs.add(frozenset((ci, cj)))
        flags[ci].add(cj); flags[cj].add(ci)
        pd_rows.append(dict(record_1=ci, record_2=cj, title_1=orig_titles[i], title_2=orig_titles[j],
                            year_1=int(years[i]), year_2=int(years[j])))
    kept["possible_duplicate_of"] = kept["record_id"].map(lambda r: "; ".join(sorted(flags.get(r, []))))
    kept["year"] = kept["year"].astype("Int64")
    kept = kept.sort_values(["year", "title"], ascending=[False, True])
    cols = ["record_id", "title", "authors", "year", "venue", "doi", "abstract", "keywords", "doc_type",
            "sources", "n_sources", "gs_rank", "blocks_found", "all_blocks", "possible_duplicate_of", "url"]
    kept[cols].to_csv(os.path.join(a.out, "records_for_screening.csv"), index=False, encoding="utf-8-sig")

    # RIS for Rayyan / Zotero / EndNote
    with open(os.path.join(a.out, "records_for_screening.ris"), "w", encoding="utf-8") as fh:
        for _, r in kept.iterrows():
            ty = "CONF" if re.search(r"conf|proceed", r["doc_type"], re.I) else "JOUR"
            fh.write(f"TY  - {ty}\nID  - {r['record_id']}\nTI  - {r['title']}\n")
            for au in re.split(r";\s*", r["authors"]) if r["authors"] else []:
                if au:
                    fh.write(f"AU  - {au}\n")
            if pd.notna(r["year"]):
                fh.write(f"PY  - {r['year']}\n")
            if r["venue"]:
                fh.write(f"T2  - {r['venue']}\n")
            if r["doi"]:
                fh.write(f"DO  - {r['doi']}\n")
            if r["abstract"]:
                fh.write(f"AB  - {r['abstract']}\n")
            for kw in re.split(r";\s*", r["keywords"]) if r["keywords"] else []:
                if kw:
                    fh.write(f"KW  - {kw}\n")
            fh.write(f"N1  - Sources: {r['sources']}; blocks: {r['blocks_found']}\n")
            if r["url"]:
                fh.write(f"UR  - {r['url']}\n")
            fh.write("ER  - \n\n")

    log = pd.DataFrame(log_rows)
    other_log = other[["source", "file", "title", "year", "doi"]].assign(reason=other["reason"], kept_record="", kept_source="")
    full_log = pd.concat([other_log, log], ignore_index=True)
    # every merge made on the title alone (no shared DOI), for manual checking
    if len(log):
        log[log["matched_by"] == "title"].sort_values("title_similarity").to_csv(
            os.path.join(a.out, "title_based_merges.csv"), index=False, encoding="utf-8-sig")
    full_log.to_csv(os.path.join(a.out, "removal_log.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(pd_rows).to_csv(os.path.join(a.out, "possible_duplicates.csv"), index=False, encoding="utf-8-sig")

    # ---- 3. counts
    dup_same = int((log["reason"] == "duplicate (same source)").sum()) if len(log) else 0
    dup_other = int((log["reason"] == "duplicate (other source)").sum()) if len(log) else 0
    lines = ["PRISMA 2020 identification counts", "=" * 34]
    for s, c in identified.items():
        lines.append(f"Records identified, {s}: {c:,}")
    lines += [f"Records identified, total: {len(df):,}", "",
              f"Duplicate records removed: {dup_same + dup_other:,}",
              f"   within one source: {dup_same:,}",
              f"   found in another source: {dup_other:,}",
              f"   matched by DOI: {int((log['matched_by'] == 'DOI').sum()):,}",
              f"   matched by title, year and first author: {int((log['matched_by'] == 'title').sum()):,} "
              "(listed in title_based_merges.csv)",
              f"   judged duplicates by hand (--manual): {manual_merged}",
              "Records marked ineligible by automation tools: 0",
              f"Records removed for other reasons: {len(other):,}"]
    for r_, c in other["reason"].value_counts().items():
        lines.append(f"   {r_}: {c}")
    lines += [f"Records to screen (title and abstract): {len(kept):,}", "",
              f"Check: {len(df):,} - {dup_same + dup_other:,} - {len(other):,} = "
              f"{len(df) - dup_same - dup_other - len(other):,}",
              f"Possible duplicates flagged for manual check (same title, different DOIs): {len(pd_rows)} pairs",
              f"Records with all three concept blocks in title/abstract/keywords: {(kept['all_blocks'] == 'Y').sum():,}",
              "", "Unique records by number of sources that found them:"]
    for k, c in kept["n_sources"].value_counts().sort_index().items():
        lines.append(f"   found in {k} source(s): {c:,}")
    lines.append("")
    lines.append("Unique records found only in one source:")
    only = kept[kept["n_sources"] == 1]["sources"].value_counts()
    for s in SOURCE_ORDER:
        if s in only:
            lines.append(f"   {s}: {only[s]:,}")
    assert len(df) - dup_same - dup_other - len(other) == len(kept), "counts do not add up"
    text = "\n".join(lines)
    open(os.path.join(a.out, "prisma_counts.txt"), "w").write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
