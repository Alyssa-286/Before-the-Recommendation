"""Render the manuscript from fixed prose + computed results (no hand-typed numbers).

Inputs: manuscript/sections_fixed.md, manuscript/sections_discussion.md (prose with
{{token}} placeholders), artifacts/analysis/*_results.json, artifacts/data_quality_audit.json,
references/verified_references.json, outputs/tables/*.md.
Outputs: manuscript/paper.md, manuscript/paper.docx, manuscript/manuscript_tokens.json.
Fails if any {{token}} is unresolved.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

MODEL = {"google_gemini": "Gemini 3.1 Flash-Lite", "mistral": "Ministral 14B"}
OUT = {"clarification": "clarification rate", "representation_error": "representation error D",
       "recommended_utility": "recommendation utility", "regret": "regret"}
ROBUST = {"robust_template": "alternate request template", "robust_order": "permuted product order", "robust_cue_location": "relocated cue set"}


def load(path: str):
    p = ROOT / path
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def f(x, d=3):
    return "n/a" if x is None else f"{x:.{d}f}"


def fp(x) -> str:
    return "n/a" if x is None else ("< 0.001" if x < 0.001 else f"= {x:.3f}")


def est(p: dict, d=3) -> str:
    if p is None or p.get("estimate") is None:
        return "not estimable"
    return f"{p['estimate']:+.{d}f} (95% CI {p['ci_low']:+.{d}f} to {p['ci_high']:+.{d}f})"


def excludes_zero(p: dict) -> bool:
    return p.get("estimate") is not None and (p["ci_low"] > 0 or p["ci_high"] < 0)


def verdict(p: dict) -> str:
    if p.get("estimate") is None:
        return "could not be estimated"
    return "the interval excludes zero" if excludes_zero(p) else "the interval includes zero"


def pct(x):
    return "n/a" if x is None else f"{100 * x:.1f}%"


def build_tokens() -> dict[str, str]:
    R = load("artifacts/analysis/core_results.json")
    A = load("artifacts/data_quality_audit.json")
    S = load("artifacts/core_run_summary.json")
    t: dict[str, str] = {}
    t["n_planned"] = f"{R['n_planned_runs']:,}"
    t["n_valid"] = f"{R['n_valid_runs']:,}"
    t["n_failed"] = f"{R['n_planned_runs'] - R['n_valid_runs']:,}"
    t["valid_pct"] = pct(R["n_valid_runs"] / R["n_planned_runs"])
    t["n_scenarios"] = str(R["n_scenarios"])
    for m in MODEL:
        bm = A["counts_by_model"][m]
        t[f"{m}_valid"] = f"{bm['valid']:,}"
        t[f"{m}_failed"] = f"{bm['failed']:,}"
        prov = load("artifacts/core_attempt_provenance.json")["models"][m]
        t[f"{m}_tech_retries"] = str(prov["technical_retries_scheduled"])
        t[f"{m}_requeued"] = str(prov["trials_requeued_after_interruption"])
        t[f"{m}_parser_retries"] = str(bm["parser_retries"])
    t["audit_checks"] = str(len(A["checks"]))
    t["audit_passed"] = "passed" if A["all_checks_passed"] else "FAILED"
    req = next(c for c in A["checks"] if c["check"] == "no_ground_truth_leakage_in_model_visible_requests")
    t["requests_scanned"] = f"{req['requests_checked']:,}"
    tok = S["tokens"]
    t["total_calls"] = f"{sum(v['provider_calls'] for v in tok.values()):,}"
    t["total_tokens"] = f"{sum(v['input'] + v['output'] for v in tok.values()):,}"
    prim = R["primary_commercial_vs_neutral_ambiguous"]
    for o in OUT:
        t[f"prim_{o}"] = est(prim[o]["pooled"])
        t[f"prim_{o}_verdict"] = verdict(prim[o]["pooled"])
        t[f"prim_{o}_holm"] = fp(prim[o]["pooled"].get("holm_adjusted_p"))
        for m in MODEL:
            t[f"prim_{o}_{m}"] = est(prim[o]["by_model"][m])
            t[f"prim_{o}_{m}_verdict"] = verdict(prim[o]["by_model"][m])
        for key, name in (("secondary_commercial_vs_neutral_explicit", "exp"), ("secondary_moderation_ambiguous_minus_explicit", "mod"), ("h1_ambiguous_minus_explicit_all_arms", "h1")):
            t[f"{name}_{o}"] = est(R[key][o]["pooled"])
            t[f"{name}_{o}_verdict"] = verdict(R[key][o]["pooled"])
            for m in MODEL:
                t[f"{name}_{o}_{m}"] = est(R[key][o]["by_model"][m])
                t[f"{name}_{o}_{m}_verdict"] = verdict(R[key][o]["by_model"][m])
        for cue in ("scarcity", "social_proof", "discount"):
            p = R["secondary_cue_specific_ambiguous"][o][cue]["pooled"]
            t[f"cue_{cue}_{o}"] = est(p)
            t[f"cue_{cue}_{o}_verdict"] = verdict(p)
    d = R["descriptives"]
    for m in MODEL:
        for g in ("ambiguous", "explicit"):
            for k in ("neutral", "scarcity", "social_proof", "discount"):
                c = d[f"{m}|{g}|{k}"]
                t[f"clar_{m}_{g}_{k}"] = pct(c["clarification_rate"])
                t[f"D_{m}_{g}_{k}"] = f(c["representation_error_mean"])
                t[f"U_{m}_{g}_{k}"] = f(c["utility_mean"])
                t[f"R_{m}_{g}_{k}"] = f(c["regret_mean"], 4)
                t[f"R0_{m}_{g}_{k}"] = pct(c["regret_zero_share"])
                t[f"cueev_{m}_{g}_{k}"] = pct(c["evidence_mentions_cue_rate"])
                t[f"topcued_{m}_{g}_{k}"] = pct(c["top_is_cued_rate"])
                t[f"unc_{m}_{g}_{k}"] = f(c["uncertainty_mean"], 2)
    sec = R["secondary_outcomes_commercial_vs_neutral"]
    for g in ("ambiguous", "explicit"):
        for o in ("cued_mean_rank", "top_is_cued", "evidence_mentions_cue", "uncertainty", "price_question", "constraint_violated"):
            t[f"sec_{g}_{o}"] = est(sec[g][o]["pooled"])
            t[f"sec_{g}_{o}_verdict"] = verdict(sec[g][o]["pooled"])
            for m in MODEL:
                t[f"sec_{g}_{o}_{m}"] = est(sec[g][o]["by_model"][m])
                t[f"sec_{g}_{o}_{m}_verdict"] = verdict(sec[g][o]["by_model"][m])
    h5 = R["h5_exploratory_discount_vs_neutral_price_question"]["ambiguous"]
    t["h5_pooled"] = est(h5["pooled"]); t["h5_verdict"] = verdict(h5["pooled"])
    for m in MODEL:
        t[f"h5_{m}"] = est(h5["by_model"][m])
    h4 = R["h4_representation_recommendation_separation"]
    for key in ("pooled|ambiguous", *(f"{m}|ambiguous" for m in MODEL)):
        lab = key.replace("|", "_")
        t[f"h4_{lab}_pairs"] = str(h4[key]["matched_pairs"])
        t[f"h4_{lab}_topchg"] = pct(h4[key]["top_product_changed_rate"])
        t[f"h4_{lab}_shift"] = f(h4[key]["weight_shift_vs_neutral_mean"])
        t[f"h4_{lab}_shift_same_top"] = pct(h4[key]["share_weight_shift_gt_0_05_with_same_top_product"])
        t[f"h4_{lab}_shifted"] = pct(h4[key]["share_weight_shift_gt_0_05"])
    st = R["repeat_stability"]
    for m in MODEL:
        t[f"stab_{m}_clar"] = pct(st[m]["clarification_decision_agreement"])
        t[f"stab_{m}_top"] = pct(st[m]["top_product_agreement"])
        t[f"stab_{m}_spread"] = f(st[m]["weight_spread_mean_max_pairwise_half_l1"])
    tax = R["failure_taxonomy"]
    for cat, v in tax["all"].items():
        t[f"tax_{cat}"] = f"{v['count']:,}"
        for m in MODEL:
            t[f"tax_{cat}_{m}"] = f"{tax[m][cat]['count']:,}"
    for m in MODEL:
        fails = R["missingness"][m]["terminal_failures"]
        t[f"fail_detail_{m}"] = ", ".join(f"{k.replace('_', ' ')} ({v})" for k, v in sorted(fails.items())) or "none"
    qt = R["question_targets"]
    for m in MODEL:
        amb = [v for k, v in qt.get(m, {}).items() if k.startswith("ambiguous")]
        counts: dict[str, int] = {}
        for v in amb:
            for k2, n in v["normalized_target_counts"].items():
                counts[k2] = counts.get(k2, 0) + n
        total = sum(counts.values()) or 1
        t[f"qt_{m}"] = "; ".join(f"{k.replace('_', ' ')} {100 * n / total:.0f}%" for k, n in sorted(counts.items(), key=lambda kv: -kv[1]))
    fm = R["factorial_models"]
    for o in OUT:
        model = fm.get(o, {})
        t[f"fm_{o}_note"] = ("fit failed: " + model["failure_reason"]) if model.get("fit_failed") else f"{model.get('family', '')}, n = {model.get('n_runs')}, {model.get('n_clusters')} scenario clusters"
    for name, label in ROBUST.items():
        rr = load(f"artifacts/analysis/{name}_results.json")
        ra = load(f"artifacts/data_quality_audit_{name}.json")
        if rr is None:
            t[f"{name}_status"] = "not run"
            for o in OUT:
                t[f"{name}_{o}"] = "not run"; t[f"{name}_{o}_verdict"] = "not run"
            continue
        t[f"{name}_status"] = f"{rr['n_valid_runs']:,} of {rr['n_planned_runs']:,} runs valid; audit {'passed' if ra and ra['all_checks_passed'] else 'not passed'}"
        for o in OUT:
            p = rr["primary_commercial_vs_neutral_ambiguous"][o]["pooled"]
            t[f"{name}_{o}"] = est(p); t[f"{name}_{o}_verdict"] = verdict(p)
    # ---- hypothesis verdicts by pre-set rules (95% CI excludes zero in the stated direction) ----
    def direction(pd: dict, sign: int) -> bool:
        return pd.get("estimate") is not None and (pd["ci_low"] > 0 if sign > 0 else pd["ci_high"] < 0)

    def hv(block: dict, sign: int | None) -> str:
        pooled = block["pooled"]; models = [block["by_model"][m] for m in MODEL]
        test = (lambda q: excludes_zero(q)) if sign is None else (lambda q: direction(q, sign))
        n_models = sum(test(q) for q in models)
        if test(pooled) and n_models == 2:
            return "supported (pooled and in both model families)"
        if test(pooled):
            return f"supported in the pooled estimate but in only {n_models} of 2 model families"
        if n_models:
            return "not supported in the pooled estimate; supported in one model family only"
        return "not supported (95% intervals include zero, pooled and per model)"
    t["H1_verdict"] = hv(R["h1_ambiguous_minus_explicit_all_arms"]["representation_error"], +1)
    t["H2_verdict"] = hv(prim["representation_error"], None)
    mod = R["secondary_moderation_ambiguous_minus_explicit"]["representation_error"]
    t["H3_verdict"] = ("supported (ambiguous-minus-explicit difference in ΔD excludes zero)" if excludes_zero(mod["pooled"])
                       else "not supported (the moderation contrast includes zero)")
    sep = h4["pooled|ambiguous"]
    util_null = not excludes_zero(prim["recommended_utility"]["pooled"])
    rep_shift = excludes_zero(prim["representation_error"]["pooled"]) or sep["share_weight_shift_gt_0_05"] > 0
    d_null = not excludes_zero(prim["representation_error"]["pooled"])
    if util_null and rep_shift:
        t["H4_verdict"] = "consistent with separation: the utility contrast includes zero while represented weights shift relative to the matched neutral run"
    elif not util_null and d_null:
        t["H4_verdict"] = ("not supported in the stated direction; the observed dissociation runs the other way: utility changed "
                           "while representation error did not")
    elif not util_null:
        t["H4_verdict"] = "not supported: utility and representation error both changed"
    else:
        t["H4_verdict"] = "indeterminate"
    pd_ = prim["representation_error"]["pooled"]; h1d = R["h1_ambiguous_minus_explicit_all_arms"]["representation_error"]["pooled"]["estimate"]
    t["dD_bound_share"] = pct(max(abs(pd_["ci_low"]), abs(pd_["ci_high"])) / abs(h1d)) if h1d else "n/a"
    t["H5_verdict"] = "exploratory; under ambiguous goals " + verdict(h5["pooled"])
    h5e = R["h5_exploratory_discount_vs_neutral_price_question"].get("explicit")
    t["h5_explicit"] = est(h5e["pooled"]) if h5e else "n/a"
    t["h5_explicit_verdict"] = verdict(h5e["pooled"]) if h5e else "n/a"
    for m in MODEL:
        rows = [v for k, v in qt.get(m, {}).items()]
        n = sum(v["n_clarifications"] for v in rows)
        sup = sum(v["answer_supported_rate"] * v["n_clarifications"] for v in rows)
        t[f"supported_{m}"] = pct(sup / n if n else None)
        t[f"nclar_{m}"] = f"{n:,}"
    return t


COMPOUND_SURNAMES = ("Horta Ribeiro",)


def _apa_name(full: str) -> str:
    for compound in COMPOUND_SURNAMES:
        if full.endswith(compound):
            given = full[: -len(compound)].split()
            return f"{compound}, " + " ".join(f"{q[0]}." for q in given)
    parts = full.replace(".", ". ").split()
    last = parts[-1]
    initials = " ".join(f"{q[0]}." for q in parts[:-1] if q[0].isalpha())
    return f"{last}, {initials}".strip().rstrip(",")


def _apa_authors(names: list[str]) -> str:
    names = [_apa_name(n) for n in names]
    if len(names) == 1:
        return names[0]
    if len(names) <= 20:
        return ", ".join(names[:-1]) + ", & " + names[-1]
    return ", ".join(names[:19]) + ", ... " + names[-1]


def _arxiv_full_authors() -> dict[str, list[str]]:
    import xml.etree.ElementTree as ET
    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ET.parse(ROOT / "references" / "arxiv_abstracts.xml").getroot()
    out = {}
    for e in root.findall("a:entry", ns):
        arxiv_id = e.find("a:id", ns).text.rsplit("/", 1)[-1].split("v")[0]
        out[arxiv_id] = [a.find("a:name", ns).text for a in e.findall("a:author", ns)]
    return out


def references_md() -> str:
    """APA 7 reference list built only from verified records (arXiv API / Crossref)."""
    from collections import Counter
    V = load("references/verified_references.json")
    full = _arxiv_full_authors()
    items = []
    for e in V["arxiv"]:
        if e["status"] != "verified":
            continue
        aid = e["arxiv_id"].split("v")[0]
        authors = full.get(aid) or [a for a in e["authors"] if a != "et al."]
        title = e["title"].replace("$τ$", "τ")
        items.append([_apa_authors(authors), e["published"][:4], f"*{title}* [Preprint]. arXiv:{aid}. https://arxiv.org/abs/{aid}", title])
    for e in V["doi"]:
        if e["status"] != "verified":
            continue
        title = html.unescape(e["title"])
        pages = (e["pages"] or "").replace("-", "–")
        items.append([_apa_authors(e["authors"]), str(e["year"]), f"{title}. *{html.unescape(e['journal'])}*, *{e['volume']}*({e['issue']}), {pages}. https://doi.org/{e['doi']}", title])
    items.sort(key=lambda it: (it[0].casefold(), it[1], it[3].casefold()))
    counts = Counter((it[0], it[1]) for it in items)
    seen: Counter = Counter()
    lines = []
    for auth, year, rest, _ in items:
        suffix = ""
        if counts[(auth, year)] > 1:
            suffix = "abcdefgh"[seen[(auth, year)]]
            seen[(auth, year)] += 1
        lines.append(f"{auth} ({year}{suffix}). {rest}")
    return "## References\n\n" + "\n\n".join(lines) + "\n"


def fill(text: str, tokens: dict[str, str]) -> str:
    def sub(m):
        key = m.group(1)
        if key not in tokens:
            raise KeyError(f"Unresolved manuscript token: {key}")
        return tokens[key]
    return re.sub(r"\{\{([a-zA-Z0-9_|]+)\}\}", sub, text)


def table(name: str) -> str:
    return (ROOT / "outputs" / "tables" / f"{name}.md").read_text(encoding="utf-8")


def main() -> None:
    tokens = build_tokens()
    fixed = (ROOT / "manuscript" / "sections_fixed.md").read_text(encoding="utf-8")
    disc = (ROOT / "manuscript" / "sections_discussion.md").read_text(encoding="utf-8")
    disc = disc.replace("[[TABLE3]]", table("table3_primary_results")).replace("[[TABLE_MODEL]]", table("table_model_specific_results")) \
        .replace("[[TABLE4]]", table("table4_robustness_results")).replace("[[TABLE5]]", table("table5_failure_taxonomy")) \
        .replace("[[TABLE1]]", table("table1_experimental_conditions")).replace("[[TABLE2]]", table("table2_scenario_construction")) \
        .replace("[[TABLE_METRICS]]", table("table_metric_definitions"))
    if "[[VERIFY]]" in disc:
        raise SystemExit("Interpretive sentences marked [[VERIFY]] must be checked against results before rendering.")
    head, body = fixed.split("## 1. Introduction", 1)
    abstract_kw, rest = disc.split("<!-- BODY -->", 1)
    paper = fill(head + abstract_kw + "\n## 1. Introduction" + body + "\n" + rest, tokens) + "\n" + references_md()
    out = ROOT / "manuscript" / "paper.md"
    out.write_text(paper, encoding="utf-8")
    (ROOT / "manuscript" / "manuscript_tokens.json").write_text(json.dumps(tokens, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    body_only = paper.split("## References")[0]
    body_only = re.sub(r"^\|.*\|$", "", body_only, flags=re.M)  # exclude tables
    words = len(re.findall(r"[A-Za-z0-9₹%][\w.,%₹'’\-]*", body_only))
    print("words (excluding references and tables):", words)
    (ROOT / "manuscript" / "word_count.json").write_text(json.dumps({"words_excluding_references_and_tables": words}) + "\n", encoding="utf-8")
    to_docx(paper, ROOT / "manuscript" / "paper.docx")
    to_pdf(paper, ROOT / "manuscript" / "paper.pdf")


def to_pdf(md: str, path: Path) -> None:
    import markdown
    import matplotlib
    from xhtml2pdf import pisa
    font_dir = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    regular, bold = (font_dir / "DejaVuSerif.ttf").as_uri(), (font_dir / "DejaVuSerif-Bold.ttf").as_uri()
    italic = (font_dir / "DejaVuSerif-Italic.ttf").as_uri()
    body = markdown.markdown(md, extensions=["tables"])
    body = body.replace('src="../', f'src="{(ROOT).as_uri()}/')
    # xhtml2pdf's default list bullet is missing from the embedded font; use explicit bullets.
    body = re.sub(r"</?[uo]l>", "", body)
    body = re.sub(r"<li>(.*?)</li>", lambda m: '<p class="li">&#8226;&#160;' + m.group(1) + "</p>", body, flags=re.S)
    css = f"""
    @font-face {{ font-family: Body; src: url('{regular}'); }}
    @font-face {{ font-family: Body; src: url('{bold}'); font-weight: bold; }}
    @font-face {{ font-family: Body; src: url('{italic}'); font-style: italic; }}
    @page {{ size: a4; margin: 2.2cm 2.2cm 2.2cm 2.2cm; }}
    body {{ font-family: Body; font-size: 10.5pt; line-height: 1.4; }}
    h1 {{ font-size: 16pt; }} h2 {{ font-size: 13pt; margin-top: 14pt; }} h3 {{ font-size: 11pt; }}
    table {{ border: 0.5pt solid #888; font-size: 7.5pt; }} td, th {{ padding: 2pt; border: 0.5pt solid #bbb; }}
    img {{ width: 16cm; }} p.li {{ margin-left: 0.6cm; text-indent: -0.4cm; margin-top: 2pt; margin-bottom: 2pt; }} blockquote {{ margin-left: 1cm; font-style: italic; }}
    """
    html_doc = f"<html><head><meta charset='utf-8'><style>{css}</style></head><body>{body}</body></html>"
    with path.open("wb") as fh:
        result = pisa.CreatePDF(html_doc, dest=fh, encoding="utf-8")
    if result.err:
        raise RuntimeError("PDF rendering failed")


def to_docx(md: str, path: Path) -> None:
    from docx import Document
    from docx.shared import Pt, Inches
    doc = Document()
    style = doc.styles["Normal"]; style.font.name = "Times New Roman"; style.font.size = Pt(12)
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                if not re.match(r"^\|(\s*-+\s*\|)+\s*$", lines[i].replace("---", "-")):
                    rows.append([c.strip() for c in lines[i].strip("|").split("|")])
                i += 1
            rows = [r for r in rows if not all(set(c) <= {"-"} for c in r)]
            tbl = doc.add_table(rows=len(rows), cols=len(rows[0])); tbl.style = "Table Grid"
            for r, row in enumerate(rows):
                for c, cell in enumerate(row[: len(rows[0])]):
                    tbl.cell(r, c).text = cell.replace("**", "")
                    for p in tbl.cell(r, c).paragraphs:
                        for run in p.runs:
                            run.font.size = Pt(8)
            continue
        m = re.match(r"^(#{1,4}) (.*)", line)
        img = re.match(r"^!\[(.*)\]\((.*)\)", line)
        if m:
            doc.add_heading(m.group(2), level=min(len(m.group(1)), 3) if len(m.group(1)) > 1 else 0)
        elif img:
            doc.add_picture(str(ROOT / "manuscript" / img.group(2)), width=Inches(6.3))
            cap = doc.add_paragraph(img.group(1)); cap.runs[0].italic = True
        elif line.strip():
            p = doc.add_paragraph()
            for part in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*)", line.lstrip("> ").lstrip("- ") if line.startswith(("- ", "> ")) else line):
                run = p.add_run(part.strip("*") if part.startswith("*") else part)
                run.bold = part.startswith("**"); run.italic = part.startswith("*") and not part.startswith("**")
            if line.startswith("- "):
                p.style = doc.styles["List Bullet"]
        i += 1
    doc.save(path)


if __name__ == "__main__":
    main()
