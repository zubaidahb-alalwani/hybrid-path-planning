#!/usr/bin/env python3
"""
screening_reconcile.py -- merge the title-and-abstract decisions of two reviewers.

Each reviewer screens the same records in their own workbooks (made by
make_screening_batches.py): pilot_<TAG>.xlsx and screening_<TAG>_batch_XX.xlsx.
This script reads both sets and writes, in --out:

  pilot_agreement.txt        Cohen's kappa on the 100 pilot records
  decisions_both.csv         one row per record: both decisions, reasons, notes, final decision
  disagreements.xlsx         records where one reviewer forwards and the other excludes,
                             with a "Final decision" drop-down to record the outcome of discussion
  full_text_list.csv         records to retrieve for full-text assessment
  google_scholar_yield.csv   per 100 Google Scholar ranks: records, forwarded to full text
  screening_counts.txt       kappa and the numbers for the PRISMA flow diagram (Fig. 1)
  ai_pilot_check.csv         (with --ai) pilot records the AI forwarded but both reviewers excluded,
                             for a second look; an internal check only, the reviewers' decisions stay final

Decision rule (protocol S1, Section 7): a record goes to full-text assessment if either
reviewer judges it Include or Maybe. Disagreements are listed for discussion; if the
reviewers agree after discussion to exclude a record, they write "Exclude" in the Final
decision column of disagreements.xlsx and run the script again with --resolved.

Kappa is computed on the decision that matters at this stage: forward (Include or Maybe)
versus Exclude. Pilot decisions fill any pilot record left blank in a reviewer's batches.

USAGE
  python screening_reconcile.py --r1 screening/reviewer_ZA --r2 screening/reviewer_WA \
      --records merged/records_for_screening.csv --out screening_results \
      [--resolved screening_results/disagreements.xlsx]
"""
import argparse, glob, os

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

DECISIONS = {"Include", "Maybe", "Exclude"}
REASONS = {f"EC{i}" for i in range(1, 7)}


def read_book(path):
    wb = load_workbook(path, read_only=True, data_only=True)
    rows = list(wb["Screening"].iter_rows(values_only=True))
    wb.close()
    hdr = list(rows[0])
    ix = {h: hdr.index(h) for h in ("Record ID", "Decision", "Reason (EC)", "Note")}
    out = []
    for r in rows[1:]:
        if r[ix["Record ID"]] is None:
            continue
        clean = lambda v: str(v).strip() if v is not None else ""
        out.append(dict(record_id=clean(r[ix["Record ID"]]), decision=clean(r[ix["Decision"]]),
                        reason=clean(r[ix["Reason (EC)"]]), note=clean(r[ix["Note"]])))
    return pd.DataFrame(out)


def read_reviewer(folder):
    pilots = glob.glob(os.path.join(folder, "pilot_*.xlsx"))
    batches = sorted(glob.glob(os.path.join(folder, "screening_*_batch_*.xlsx")))
    if not batches:
        raise SystemExit(f"no screening_*_batch_*.xlsx files in {folder}")
    tag = os.path.basename(batches[0]).split("_")[1]
    dec = pd.concat([read_book(b).assign(batch=os.path.basename(b)) for b in batches], ignore_index=True)
    pil = read_book(pilots[0]) if pilots else pd.DataFrame(columns=["record_id", "decision", "reason", "note"])
    if len(pil):
        p = pil.set_index("record_id")
        blank = dec["decision"].eq("") & dec["record_id"].isin(p.index)
        for i in dec[blank].index:
            row = p.loc[dec.at[i, "record_id"]]
            dec.loc[i, ["decision", "reason", "note"]] = [row["decision"], row["reason"], row["note"]]
    return tag, dec, pil


def checks(tag, dec):
    out = []
    bad = dec[(dec["decision"] != "") & ~dec["decision"].isin(DECISIONS)]
    if len(bad):
        out.append(f"{tag}: {len(bad)} decisions are not Include/Maybe/Exclude (e.g. {bad['record_id'].iloc[0]})")
    nr = dec[(dec["decision"] == "Exclude") & ~dec["reason"].isin(REASONS)]
    if len(nr):
        out.append(f"{tag}: {len(nr)} exclusions without a valid EC reason (e.g. {nr['record_id'].iloc[0]})")
    und = int((dec["decision"] == "").sum())
    if und:
        out.append(f"{tag}: {und:,} records still undecided")
    if dec["record_id"].duplicated().any():
        out.append(f"{tag}: a Record ID appears twice")
    return out


def kappa(a, b):
    """Cohen's kappa for two binary series (1 = forward, 0 = exclude)."""
    n = len(a)
    if n == 0:
        return None, 0
    p_o = float(((a == 1) & (b == 1)).sum() + ((a == 0) & (b == 0)).sum()) / n
    pa, pb = a.mean(), b.mean()
    p_e = pa * pb + (1 - pa) * (1 - pb)
    return (None if p_e == 1 else (p_o - p_e) / (1 - p_e)), n


def fwd(s):
    return s.map(lambda d: 1 if d in ("Include", "Maybe") else (0 if d == "Exclude" else None))


def write_disagreements(df, path, t1, t2):
    F = Font(name="Arial", size=10)
    FH = Font(name="Arial", size=10, bold=True, color="FFFFFFFF")
    HF = PatternFill("solid", fgColor="FF1F4E79")
    YF = PatternFill("solid", fgColor="FFFFF2CC")
    thin = Side(style="thin", color="FFBFBFBF")
    wb = Workbook()
    ws = wb.active
    ws.title = "Disagreements"
    cols = ["Record ID", "Title", "Year", "Abstract", f"{t1} decision", f"{t1} reason", f"{t1} note",
            f"{t2} decision", f"{t2} reason", f"{t2} note", "Final decision", "Final reason (EC)", "Discussion note"]
    ws.append(cols)
    for _, r in df.iterrows():
        ws.append([r["record_id"], r["title"], int(r["year"]) if str(r["year"]).isdigit() else r["year"], r["abstract"],
                   r["decision_1"], r["reason_1"], r["note_1"], r["decision_2"], r["reason_2"], r["note_2"],
                   r.get("final_manual", "") or None, r.get("final_reason", "") or None,
                   r.get("final_note", "") or None])
    for c in ws[1]:
        c.font = FH
        c.fill = HF
        c.alignment = Alignment(wrap_text=True)
    last = len(df) + 1
    for row in ws.iter_rows(min_row=2, max_row=last):
        for c in row:
            c.font = F
            c.alignment = Alignment(wrap_text=True, vertical="top")
            c.border = Border(bottom=thin)
        for j in (10, 11, 12):
            row[j].fill = YF
    for col, w in zip("ABCDEFGHIJKLM", [9, 40, 6, 80, 10, 8, 25, 10, 8, 25, 12, 10, 30]):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "C2"
    dv = DataValidation(type="list", formula1='"Include,Maybe,Exclude"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"K2:K{max(last, 2)}")
    dv2 = DataValidation(type="list", formula1='"EC1,EC2,EC3,EC4,EC5,EC6"', allow_blank=True)
    ws.add_data_validation(dv2)
    dv2.add(f"L2:L{max(last, 2)}")
    ins = wb.create_sheet("Instructions", 0)
    for i, t in enumerate([
            "Disagreements at title and abstract: one reviewer forwards the record (Include or Maybe), the other excludes it.",
            "By the protocol these records go to full-text assessment unless both reviewers agree, after discussion, to exclude.",
            "Discuss each record together. If you agree to exclude, choose Exclude in 'Final decision' and give the reason; "
            "otherwise leave it blank or choose Include/Maybe.",
            "Then run screening_reconcile.py again with --resolved pointing to this file."], 1):
        c = ins.cell(row=i, column=1, value=t)
        c.font = F
        c.alignment = Alignment(wrap_text=True)
    ins.column_dimensions["A"].width = 120
    wb.save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--r1", required=True, help="folder of reviewer 1 workbooks")
    ap.add_argument("--r2", required=True, help="folder of reviewer 2 workbooks")
    ap.add_argument("--records", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--resolved", default="", help="disagreements.xlsx with Final decision filled in")
    ap.add_argument("--ai", default="", help="optional AI cross-check of the pilot (ai_check/pilot_AI.xlsx)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    t1, d1, p1 = read_reviewer(a.r1)
    t2, d2, p2 = read_reviewer(a.r2)
    recs = pd.read_csv(a.records, dtype=str, keep_default_na=False)
    problems = checks(t1, d1) + checks(t2, d2)
    if set(d1["record_id"]) != set(d2["record_id"]):
        problems.append("the two reviewers' files do not hold the same records")

    # ---- pilot kappa
    lines_p = ["Pilot (100 records)"]
    if len(p1) and len(p2):
        pp = p1.merge(p2, on="record_id", suffixes=("_1", "_2"))
        pp = pp[(pp["decision_1"] != "") & (pp["decision_2"] != "")]
        k, n = kappa(fwd(pp["decision_1"]).astype(float), fwd(pp["decision_2"]).astype(float))
        agree = int((fwd(pp["decision_1"]) == fwd(pp["decision_2"])).sum())
        lines_p += [f"   records decided by both: {n}", f"   agreement: {agree} of {n}",
                    f"   Cohen's kappa: {k:.2f}" if k is not None else "   Cohen's kappa: not defined",
                    "   (a kappa below 0.60 suggests clarifying the criteria and piloting again)"]
    else:
        lines_p.append("   pilot files missing or empty")
    if a.ai and len(p1) and len(p2):
        ai = read_book(a.ai)[["record_id", "decision", "reason", "note"]].rename(
            columns={"decision": "decision_ai", "reason": "reason_ai", "note": "note_ai"})
        pa = p1.merge(p2, on="record_id", suffixes=("_1", "_2")).merge(ai, on="record_id")
        pa = pa[(pa["decision_1"] != "") & (pa["decision_2"] != "")]
        lines_p += ["", "AI cross-check of the pilot (internal check, not a reviewer)"]
        for t, col in ((t1, "decision_1"), (t2, "decision_2")):
            kk, nn = kappa(fwd(pa[col]).astype(float), fwd(pa["decision_ai"]).astype(float))
            lines_p.append(f"   kappa {t} vs AI: {kk:.2f} (n = {nn})" if kk is not None else f"   kappa {t} vs AI: not defined")
        miss = pa[(fwd(pa["decision_ai"]) == 1) & (fwd(pa["decision_1"]) == 0) & (fwd(pa["decision_2"]) == 0)]
        extra = pa[(fwd(pa["decision_ai"]) == 0) & ((fwd(pa["decision_1"]) == 1) | (fwd(pa["decision_2"]) == 1))]
        lines_p += [f"   AI forwards, both reviewers exclude: {len(miss)} (listed in ai_pilot_check.csv; worth a second look)",
                    f"   AI excludes, at least one reviewer forwards: {len(extra)}"]
        miss.merge(recs[["record_id", "title", "year"]], on="record_id", how="left")[
            ["record_id", "title", "year", "decision_1", "reason_1", "decision_2", "reason_2", "decision_ai", "note_ai"]] \
            .rename(columns={"decision_1": f"decision_{t1}", "reason_1": f"reason_{t1}",
                             "decision_2": f"decision_{t2}", "reason_2": f"reason_{t2}"}) \
            .to_csv(os.path.join(a.out, "ai_pilot_check.csv"), index=False, encoding="utf-8-sig")
    open(os.path.join(a.out, "pilot_agreement.txt"), "w").write("\n".join(lines_p) + "\n")

    # ---- merge
    m = d1.merge(d2, on="record_id", suffixes=("_1", "_2"), how="outer").merge(recs, on="record_id", how="left")
    m["f1"], m["f2"] = fwd(m["decision_1"].fillna("")), fwd(m["decision_2"].fillna(""))
    both = m["f1"].notna() & m["f2"].notna()
    k, n = kappa(m.loc[both, "f1"].astype(float), m.loc[both, "f2"].astype(float))
    m["disagree"] = both & (m["f1"] != m["f2"])

    # resolved disagreements
    m["final_manual"] = m["final_reason"] = m["final_note"] = ""
    if a.resolved:
        rs = pd.read_excel(a.resolved, sheet_name="Disagreements", dtype=str).fillna("")
        rs["Record ID"] = rs["Record ID"].str.strip()
        for col, src in (("final_manual", "Final decision"), ("final_reason", "Final reason (EC)"),
                         ("final_note", "Discussion note")):
            m[col] = m["record_id"].map(dict(zip(rs["Record ID"], rs[src].str.strip()))).fillna("")
        m.loc[~m["disagree"], ["final_manual", "final_reason", "final_note"]] = ""
        bad = m[(m["final_manual"] == "Exclude") & ~m["final_reason"].isin(REASONS)]
        if len(bad):
            problems.append(f"{len(bad)} disagreements excluded after discussion without a Final reason (EC)")

    def final(r):
        if pd.isna(r["f1"]) or pd.isna(r["f2"]):
            return ""
        if r["final_manual"] in DECISIONS:
            return "Forward" if r["final_manual"] != "Exclude" else "Exclude"
        return "Forward" if (r["f1"] == 1 or r["f2"] == 1) else "Exclude"
    m["final"] = m.apply(final, axis=1)

    keep = ["record_id", "decision_1", "reason_1", "note_1", "decision_2", "reason_2", "note_2", "disagree",
            "final_manual", "final_reason", "final_note", "final", "title", "year", "doi", "sources"]
    m[keep].rename(columns={"decision_1": f"decision_{t1}", "reason_1": f"reason_{t1}", "note_1": f"note_{t1}",
                            "decision_2": f"decision_{t2}", "reason_2": f"reason_{t2}", "note_2": f"note_{t2}"}) \
        .to_csv(os.path.join(a.out, "decisions_both.csv"), index=False, encoding="utf-8-sig")
    write_disagreements(m[m["disagree"]].fillna(""), os.path.join(a.out, "disagreements.xlsx"), t1, t2)
    ft = m[m["final"] == "Forward"]
    ft[["record_id", "decision_1", "decision_2", "title", "authors", "year", "venue", "doi", "url", "sources"]] \
        .to_csv(os.path.join(a.out, "full_text_list.csv"), index=False, encoding="utf-8-sig")

    gs = m[m["gs_rank"].fillna("") != ""].copy()
    if len(gs):
        gs["block"] = ((pd.to_numeric(gs["gs_rank"]) - 1) // 100 * 100 + 1).astype(int)
        gs["only_gs"] = gs["sources"].eq("Google Scholar")
        gs["fwd"] = gs["final"].eq("Forward")
        y = gs.groupby("block").agg(records_to_screen=("record_id", "size"), only_in_google_scholar=("only_gs", "sum"),
                                    forwarded=("fwd", "sum"))
        y["forwarded_only_in_google_scholar"] = gs[gs["only_gs"]].groupby("block")["fwd"].sum()
        y = y.fillna(0).astype(int)
        y.index = [f"{b}-{b + 99}" for b in y.index]
        y.to_csv(os.path.join(a.out, "google_scholar_yield.csv"), index_label="ranks")

    decided = int((m["final"] != "").sum())
    n_fwd, n_exc = int((m["final"] == "Forward").sum()), int((m["final"] == "Exclude").sum())
    resolved_excl = int(((m["final_manual"] == "Exclude") & m["disagree"]).sum())
    lines = ["Title and abstract screening by two reviewers", "=" * 45,
             f"Reviewers: {t1} and {t2}", f"Records: {len(m):,}; decided by both: {decided:,}", "",
             "Agreement (forward to full text vs exclude)",
             f"   records decided by both: {n:,}",
             f"   disagreements: {int(m['disagree'].sum()):,}",
             f"   Cohen's kappa: {k:.2f}" if k is not None else "   Cohen's kappa: not defined", "",
             "For Fig. 1 (valid once both reviewers have decided every record):",
             f"   Records screened: {len(m):,}",
             f"   Records excluded: {n_exc:,}  (of which excluded after discussion: {resolved_excl:,})",
             f"   Reports sought for retrieval: {n_fwd:,}", "",
             "Exclusion reasons on records finally excluded (agreed reason after discussion, otherwise reviewer 1's;",
             "   reviewers' reasons differ on {:,} records excluded by both):"]
    ex = m[m["final"] == "Exclude"].copy()
    ex["reason_final"] = ex["final_reason"].where(ex["final_reason"] != "", ex["reason_1"])
    lines[-1] = lines[-1].format(int(((ex["reason_1"] != ex["reason_2"]) & ~ex["disagree"]).sum()))
    for r_ in sorted(REASONS):
        lines.append(f"   {r_}: {int((ex['reason_final'] == r_).sum()):,}")
    lines += ["", "Checks:"] + ([f"   PROBLEM: {p}" for p in problems] or ["   no problems found"])
    lines += ["", *lines_p]
    text = "\n".join(lines)
    open(os.path.join(a.out, "screening_counts.txt"), "w").write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
