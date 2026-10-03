# IEEE LaTeX version

An IEEE-conference-format (`IEEEtran`, `conference` option) export of the paper. It is an **additional** export. The conference submission version is `manuscript/paper.{pdf,docx,md}` / `submission/`. Nothing here implies that the GBS marketing conference requires IEEE format; check the official call.

## Files

- `paper_ieee.tex`: full paper (title block placeholders, abstract, index terms, all sections, equations, figures, tables, bibliography)
- `references.bib`: BibTeX for the 16 cited works, all verified (`references/verified_references.json`)
- `figures/`: the final figures generated from the experiment data (`outputs/figures/`)
- `tables/`: LaTeX tables generated from `outputs/tables/*.csv`
- `paper_ieee.pdf`: compiled output

## Build

The source is generated, so the numbers stay synchronized with the analysis:

```bash
python scripts/build_ieee.py
```

Then compile, from `paper/ieee/`:

```bash
pdflatex paper_ieee && bibtex paper_ieee && pdflatex paper_ieee && pdflatex paper_ieee
```

Verified with MiKTeX 24.1 pdfLaTeX: 0 errors, 0 undefined citations or references, 0 overfull boxes.

Before submission, replace the `[Author Name(s)]`, `[Department, Institution]`, `[City, Country]` and `[email address]` placeholders.
