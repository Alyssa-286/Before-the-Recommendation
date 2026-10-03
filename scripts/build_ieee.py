"""Build the IEEE LaTeX package (paper/ieee/) from the rendered manuscript.

Sources: manuscript/paper.md (token-rendered from analysis outputs),
outputs/figures/*.png, outputs/tables/*.csv, references/verified_references.json.
No number is typed here. Fails if any author-year citation cannot be mapped to a
verified BibTeX key.
"""

from __future__ import annotations

import csv
import html
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "ieee"

# key: (arXiv id or DOI, citation patterns as written in the manuscript)
CITES = {
    "bettman1998constructive": ("10.1086/209535", ["Bettman et al., 1998", "Bettman et al. (1998)"]),
    "haubl2000consumer": ("10.1287/mksc.19.1.4.15178", ["Häubl & Trifts, 2000", "Häubl and Trifts (2000)"]),
    "lynn1991scarcity": ("10.1002/mar.4220080105", ["e.g., Lynn, 1991", "Lynn, 1991", "Lynn (1991)"]),
    "fang2025toomany": ("10.1177/00222429251326941", ["Fang et al. (2025)", "Fang et al., 2025"]),
    "saracay2026beyond": ("2606.30863", ["Saracay et al., 2026", "Saracay et al. (2026)"]),
    "tran2026entropy": ("2603.11399", ["Tran et al., 2026", "Tran et al. (2026)"]),
    "narasimhan2026taurec": ("2606.10156", ["Narasimhan & Narasimhan, 2026"]),
    "yu2026shopping": ("2603.14864", ["Yu et al., 2026"]),
    "yang2026apeb": ("2607.03162", ["Yang et al., 2026"]),
    "peng2025survey": ("2502.10050", ["Peng et al. (2025)", "Peng et al., 2025"]),
    "wadi2026shopping": ("2609.28372", ["Wadi and Ma (2026a)", "Wadi & Ma, 2026a"]),
    "wadi2026whom": ("2609.17989", ["Wadi and Ma (2026b)", "Wadi & Ma, 2026b"]),
    "alavi2026agents": ("2604.26220", ["Alavi and Nozari (2026)", "Alavi & Nozari, 2026"]),
    "werner2024experimental": ("2409.12143", ["Werner et al., 2024", "Werner et al. (2024)"]),
    "salvi2026commercial": ("2604.04263", ["Salvi et al., 2026", "Salvi et al. (2026)"]),
    "li2026selective": ("2609.36614", ["Li, 2026", "Li (2026)"]),
}

TABLES = [  # caption prefix in paper.md -> csv name, label, wide?
    ("Table 1.", "table1_experimental_conditions", "tab:conditions", True),
    ("Metric definitions", "table_metric_definitions", "tab:metrics", True),
    ("Table 2.", "table2_scenario_construction", "tab:scenarios", True),
    ("Table 3.", "table3_primary_results", "tab:primary", True),
    ("Model-specific", "table_model_specific_results", "tab:models", True),
    ("Table 4.", "table4_robustness_results", "tab:robustness", True),
    ("Table 5.", "table5_failure_taxonomy", "tab:failures", True),
]

CHARS = [
    ("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("#", r"\#"), ("_", r"\_"), ("$", r"\$"),
    ("{", r"\{"), ("}", r"\}"), ("^", r"\^{}"),
    ("₹", "INR~"), ("ΔD", r"$\Delta D$"), ("Δ", r"$\Delta$"), ("ŵ", r"$\hat{w}$"), ("w*", r"$w^{*}$"),
    ("≤", r"$\le$"), ("≥", r"$\ge$"), ("−", r"$-$"), ("×", r"$\times$"), ("½", r"$\tfrac{1}{2}$"),
    ("Σ", r"$\Sigma$"), ("τ", r"$\tau$"), ("~", r"\textasciitilde{}"), ("→", r"$\rightarrow$"), ("…", r"\ldots{}"),
    ("’", "'"), ("“", "``"), ("”", "''"),
]


def esc(text: str) -> str:
    out = []
    i = 0
    while i < len(text):
        for src, dst in CHARS:
            if text.startswith(src, i):
                out.append(dst)
                i += len(src)
                break
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def inline(text: str) -> str:
    """Escape plain text, then apply bold/italic/code markup."""
    text = re.sub(r'"([^"]+)"', lambda m: "“" + m.group(1) + "”", text)
    parts = re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)", text)
    res = []
    for part in parts:
        if part.startswith("**") and part.endswith("**"):
            res.append(r"\textbf{" + esc(part[2:-2]) + "}")
        elif part.startswith("`") and part.endswith("`"):
            res.append(r"\texttt{" + esc(part[1:-1]) + "}")
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            res.append(r"\emph{" + esc(part[1:-1]) + "}")
        else:
            res.append(esc(part))
    return "".join(res)


def cite_pass(text: str) -> str:
    """Replace author-year citations (raw markdown text) with placeholders before escaping."""
    pattern_to_key = sorted(((p, k) for k, (_, ps) in CITES.items() for p in ps), key=lambda x: -len(x[0]))

    def paren(m: re.Match) -> str:
        inner = m.group(1)
        parts = [x.strip() for x in inner.split(";")]
        keys = []
        for part in parts:
            key = next((k for p, k in pattern_to_key if part == p), None)
            if key is None:
                return m.group(0)
            keys.append(key)
        return f"@@CITE{{{','.join(keys)}}}@@"

    text = re.sub(r"\(([^()]*?\d{4}[ab]?)\)", paren, text)
    for p, k in pattern_to_key:
        if "(" in p:  # narrative form: Author (year) -> Author~[n]
            author = p.split(" (")[0]
            text = text.replace(p, f"{author}@@CITE{{{k}}}@@")
    return text


def finish_cites(latex: str) -> str:
    return re.sub(r"@@CITE\\\{([^}]*)\\\}@@", lambda m: "~\\cite{" + m.group(1).replace("\\_", "_") + "}", latex)


def table_latex(name: str, label: str, caption: str, wide: bool) -> str:
    rows = list(csv.reader((ROOT / "outputs" / "tables" / f"{name}.csv").open(encoding="utf-8")))
    header, body = rows[0], rows[1:]
    n = len(header)
    spec = "@{}" + "".join("X" if i in (0, n - 1) or n <= 3 else ">{\\raggedright\\arraybackslash}X" for i in range(n)) + "@{}"
    spec = "@{}" + " ".join([">{\\raggedright\\arraybackslash}X"] * n) + "@{}"
    env = "table*" if wide else "table"
    width = r"\textwidth" if wide else r"\columnwidth"
    lines = [rf"\begin{{{env}}}[t]", r"\centering", r"\scriptsize", rf"\caption{{{esc(caption)}}}", rf"\label{{{label}}}",
             rf"\begin{{tabularx}}{{{width}}}{{{spec}}}", r"\toprule", " & ".join(r"\textbf{" + esc(h) + "}" for h in header) + r" \\", r"\midrule"]
    for r in body:
        lines.append(" & ".join(esc(c) for c in r) + r" \\")
    lines += [r"\bottomrule", r"\end{tabularx}", rf"\end{{{env}}}"]
    return "\n".join(lines)


def bib() -> str:
    V = json.loads((ROOT / "references" / "verified_references.json").read_text(encoding="utf-8"))
    sys.path.insert(0, str(ROOT / "scripts"))
    import render_manuscript
    full = render_manuscript._arxiv_full_authors()
    by_id = {e["arxiv_id"].split("v")[0]: e for e in V["arxiv"] if e["status"] == "verified"}
    by_doi = {e["doi"]: e for e in V["doi"] if e["status"] == "verified"}
    out = []

    def bib_name(n: str) -> str:
        for comp in render_manuscript.COMPOUND_SURNAMES:
            if n.endswith(comp):
                return f"{{{comp}}}, {n[:-len(comp)].strip()}"
        parts = n.split()
        return f"{parts[-1]}, {' '.join(parts[:-1])}"

    for key, (ident, _) in CITES.items():
        if ident in by_doi:
            e = by_doi[ident]
            authors = " and ".join(bib_name(a) for a in e["authors"])
            out.append(f"@article{{{key},\n  author = {{{authors}}},\n  title = {{{{{html.unescape(e['title'])}}}}},\n  journal = {{{html.unescape(e['journal']).replace('&', chr(92) + '&')}}},\n"
                       f"  year = {{{e['year']}}},\n  volume = {{{e['volume']}}},\n  number = {{{e['issue']}}},\n  pages = {{{(e['pages'] or '').replace('-', '--')}}},\n  doi = {{{ident}}}\n}}")
        else:
            e = by_id[ident]
            authors = " and ".join(bib_name(a) for a in (full.get(ident) or e["authors"]))
            title = e["title"].replace("$τ$", r"$\tau$")
            out.append(f"@misc{{{key},\n  author = {{{authors}}},\n  title = {{{{{title}}}}},\n  year = {{{e['published'][:4]}}},\n"
                       f"  eprint = {{{ident}}},\n  archivePrefix = {{arXiv}},\n  howpublished = {{arXiv preprint arXiv:{ident}}},\n  url = {{https://arxiv.org/abs/{ident}}}\n}}")
    return "\n\n".join(out) + "\n"


MEASURES_LATEX = r"""Representation error is the half-$L_1$ distance between the agent's weights and the controlled objective,
\begin{equation}
D_{sr}=\tfrac{1}{2}\sum_{k=1}^{K}\left|\hat{w}_{srk}-w^{*}_{sk}\right|,\label{eq:D}
\end{equation}
which ranges from 0 (identical) to 1. The cue-induced shift is the matched contrast
\begin{equation}
\Delta D = D_{\text{commercial}} - D_{\text{neutral}},\label{eq:dD}
\end{equation}
formed within scenario, model and repetition. Utility of product $p$ under scenario $s$ and regret of the top-ranked product $\hat{p}_s$ are
\begin{equation}
U(p\mid s)=\sum_{k=1}^{K} w^{*}_{sk}\,x_{pk},\qquad R_s = U(p^{*}_s\mid s)-U(\hat{p}_s\mid s),\label{eq:UR}
\end{equation}
where $x_{pk}$ are normalized factual scores and $p^{*}_s$ is the optimal feasible product. Clarification rate is the share of valid runs with a question. Secondary measures are question target, cued-product rank, evidence mentioning a cue term, reported uncertainty, repeat stability and a pre-specified failure taxonomy."""


def main() -> None:
    md = (ROOT / "manuscript" / "paper.md").read_text(encoding="utf-8").split("## References")[0]
    (OUT / "figures").mkdir(parents=True, exist_ok=True)
    (OUT / "tables").mkdir(parents=True, exist_ok=True)
    md = cite_pass(md)
    leftovers = re.findall(r"\b[A-Z][a-zä]+(?: et al\.| and [A-Z][a-z]+| & [A-Z][a-z]+)?,? \(?\d{4}[ab]?\)", md)
    if leftovers:
        raise SystemExit(f"Unmapped citations: {sorted(set(leftovers))}")

    fig_labels, tab_labels = {}, {}
    lines = md.splitlines()
    title = lines[0].lstrip("# ").strip()
    body: list[str] = []
    abstract, keywords = "", ""
    i, section = 1, None
    in_list = False
    while i < len(lines):
        line = lines[i]
        if line.startswith("|"):
            i += 1
            continue
        tcap = re.match(r"^\*\*(.+?)\*\*\s*$", line)
        if tcap and any(tcap.group(1).startswith(prefix) for prefix, *_ in TABLES):
            cap = tcap.group(1)
            prefix, name, label, wide = next(t for t in TABLES if cap.startswith(t[0]))
            num = re.match(r"Table (\d+)\.", cap)
            clean = re.sub(r"^Table \d+\.\s*", "", cap)
            (OUT / "tables" / f"{name}.tex").write_text(table_latex(name, label, clean, wide) + "\n", encoding="utf-8")
            if num:
                tab_labels[num.group(1)] = label
            body.append(rf"\input{{tables/{name}}}")
            i += 1
            continue
        img = re.match(r"^!\[(.*)\]\((.*)\)", line)
        h = re.match(r"^(#{2,3}) (.*)", line)
        if in_list and not line.startswith("- "):
            body.append(r"\end{itemize}")
            in_list = False
        if h:
            text = re.sub(r"^\d+(\.\d+)?\.?\s*", "", h.group(2)).strip()
            section = text
            if text in ("Abstract",):
                i += 1
                para = []
                while i < len(lines) and not lines[i].startswith("**Keywords"):
                    if lines[i].strip():
                        para.append(lines[i].strip())
                    i += 1
                abstract = inline(" ".join(para))
                keywords = inline(lines[i].split(":**", 1)[1].strip())
                i += 1
                continue
            body.append((r"\section{" if h.group(1) == "##" else r"\subsection{") + inline(text) + "}")
            if text == "Measures":
                body.append(MEASURES_LATEX)
                i += 1
                while i < len(lines) and not lines[i].startswith("#"):
                    i += 1
                continue
        elif img:
            cap = img.group(1)
            fname = Path(img.group(2)).name
            shutil.copy2(ROOT / "outputs" / "figures" / fname, OUT / "figures" / fname)
            num = re.match(r"Figure (\d+)\.", cap)
            label = "fig:" + Path(fname).stem
            if num:
                fig_labels[num.group(1)] = label
            clean = re.sub(r"^Figure \d+\.\s*", "", cap)
            narrow = fname.startswith(("fig1_", "fig2_"))
            env = "figure" if narrow else "figure*"
            width = r"\columnwidth" if narrow else r"0.9\textwidth"
            body.append(rf"\begin{{{env}}}[t]" + "\n" + r"\centering" + "\n" + rf"\includegraphics[width={width}]{{figures/{fname}}}" + "\n"
                        + rf"\caption{{{inline(clean)}}}" + "\n" + rf"\label{{{label}}}" + "\n" + rf"\end{{{env}}}")
        elif line.startswith("- "):
            if not in_list:
                body.append(r"\begin{itemize}")
                in_list = True
            body.append(r"\item " + inline(line[2:]))
        elif line.startswith("> "):
            body.append(r"\begin{quote}" + inline(line[2:]) + r"\end{quote}")
        elif line.startswith("[Author name"):
            pass
        elif line.strip():
            body.append(inline(line))
        else:
            body.append("")
        i += 1
    if in_list:
        body.append(r"\end{itemize}")
    text = "\n".join(body)
    text = finish_cites(text)
    abstract = finish_cites(abstract)
    # cross-references
    text = re.sub(r"Figures (\d+) and (\d+)", lambda m: f"Figs.~\\ref{{{fig_labels[m.group(1)]}}} and~\\ref{{{fig_labels[m.group(2)]}}}", text)
    text = re.sub(r"Figure (\d+)", lambda m: f"Fig.~\\ref{{{fig_labels[m.group(1)]}}}" if m.group(1) in fig_labels else m.group(0), text)
    text = re.sub(r"Table (\d+)", lambda m: f"Table~\\ref{{{tab_labels[m.group(1)]}}}" if m.group(1) in tab_labels else m.group(0), text)
    text = re.sub(r"Sections? (\d+(?:\.\d+)?)", lambda m: m.group(0), text)
    tex = rf"""\documentclass[conference]{{IEEEtran}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage{{amsmath,amssymb}}
\usepackage{{graphicx}}
\usepackage{{booktabs}}
\usepackage{{tabularx}}
\usepackage{{array}}
\usepackage{{cite}}
\usepackage{{url}}
\usepackage[hidelinks]{{hyperref}}
\renewcommand{{\tabularxcolumn}}[1]{{m{{#1}}}}
\begin{{document}}

\title{{{esc(title)}}}

\author{{\IEEEauthorblockN{{{{[Author Name(s)]}}}}
\IEEEauthorblockA{{{{[Department, Institution]}}\\
{{[City, Country]}}\\
{{[email address]}}}}}}

\maketitle

\begin{{abstract}}
{abstract}
\end{{abstract}}

\begin{{IEEEkeywords}}
{keywords}
\end{{IEEEkeywords}}

{text}

\bibliographystyle{{IEEEtran}}
\bibliography{{references}}

\end{{document}}
"""
    (OUT / "paper_ieee.tex").write_text(tex, encoding="utf-8")
    (OUT / "references.bib").write_text(bib(), encoding="utf-8")
    print("wrote", OUT / "paper_ieee.tex", "figures:", len(fig_labels), "tables:", len(list((OUT / "tables").glob("*.tex"))))


if __name__ == "__main__":
    main()
