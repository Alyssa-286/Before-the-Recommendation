# Before the Recommendation

**Do Storefront Marketing Cues Shift How AI Shopping Agents Represent Consumer Goals?**

A controlled computational audit of AI shopping agents in a synthetic laptop storefront. It tests whether ordinary storefront marketing cues (scarcity, social proof, discount framing) change an agent's clarification behaviour and its *represented* consumer goal under ambiguous versus explicit goals. Representation fidelity is kept separate from recommendation utility.

> Scope: synthetic catalog, controlled latent objectives, deterministic simulated user, two model families (Google `gemini-3.1-flash-lite`, Mistral `ministral-14b-2512`). **No human participants.** Results describe the tested model versions in this environment only.

## Repository map

| Path | Contents |
|---|---|
| `project.md` | Authoritative research specification (research lock) |
| `analysis/analysis_plan.md` | Pre-data statistical analysis plan v1.0.0 (frozen) |
| `roadmap.md` | Dated execution history, including every failure, fix and deviation |
| `configs/core_v2.json` | Frozen core environment (corrected catalog; `phase1.json` preserved) |
| `src/before_recommendation/` | Instrument: catalog, objectives, cues, prompts, simulated user, evaluator, adapters, live controller, runner, leakage check, dataset, statistics |
| `scripts/` | Entry points (see the pipeline below) |
| `tests/` | Unit/integration tests (fake transports only; no network) |
| `data/core/` | Raw core data: per-model checkpoint, append-only traces per attempt, raw model I/O per call, failures, transport and credential-request logs (credential **variable names** only) |
| `data/robust_*/` | Robustness datasets (separate from the core) |
| `data/analysis/` | Derived trial-level analysis datasets |
| `artifacts/` | Machine-readable audits, freeze, selection, manifests, analysis results |
| `outputs/figures`, `outputs/tables` | Figures and tables generated from the frozen data |
| `manuscript/` | Paper source and rendered outputs |
| `submission/` | Submission package |

## Reproducing the study

```bash
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements-lock.txt && .venv/Scripts/python -m pip install -e .
```

**Offline (no API keys needed):**

```bash
python -m unittest discover -s tests -v
```
```bash
python scripts/search_catalog_seed.py
```
```bash
python scripts/audit_core_dataset.py core
```
```bash
python scripts/run_analysis.py core
```
```bash
python scripts/make_figures_tables.py core
```
```bash
python scripts/render_manuscript.py
```

The seed search re-derives the accepted catalog and its diagnostics. The audit recomputes every metric from raw traces. Analysis, figures and the manuscript are regenerated from the saved data.

**Live re-execution (optional, needs your own keys).** Put the keys in a git-ignored `.env`, using the variable names in `src/before_recommendation/experiment_config.py`, then run:

```bash
python scripts/run_experiment.py --stage core
```

Runs are checkpointed and resume without repeating completed trials. Model outputs are stochastic (provider-default sampling), so a re-run is a replication, not a byte-identical reproduction. The archived raw outputs are the record of this study.

## Key provenance

- Phase-1 catalog was found degenerate (one product optimal for all 40 objectives); acceptance criteria were committed (`349e932`) **before** the seed search; accepted seed 20260955 (`artifacts/environment_seed_search.json`).
- Experiment freeze before any core trial: `artifacts/experiment_freeze.json` (commit `33bfa10`).
- Data-quality audit: `artifacts/data_quality_audit.json`; manifest: `artifacts/trial_manifest.json`.
- Zero-cost execution: only verified free routes were used (`artifacts/credential_capacity_audit.json`, `artifacts/gemini_tier_probe.json`). No secrets are stored in the repository.

## Results at a glance

All numbers are generated from the frozen data; see `artifacts/final_report.md` (summary), `artifacts/analysis/core_results.json` (full estimates), `manuscript/paper.pdf` (paper) and `artifacts/claim_evidence_table.md`. In brief: goal ambiguity increased representation error in both models (H1 supported); ordinary storefront cues did not change the represented goal (H2/H3 not supported; replicated in robustness datasets); in the core design cues lowered clarification and utility mainly for Ministral; these effects replicated with a relocated cue set but not under an alternate request wording or permuted product order; clarification questions were rarely answerable by the frozen single-dimension simulated user.

## Execution notes

Execution used only free API routes (Gemini FreeTier projects; Mistral Free mode) and spanned several daily quota windows. Long runs were launched as WMI-created processes so they survive agent-session restarts; every resume continued from the SQLite checkpoint (see `roadmap.md` and `artifacts/core_attempt_provenance.json`). Data schema: `docs/DATA_SCHEMA.md`.

## Integrity rules

No fabricated data or citations; failed runs are preserved and counted; hypotheses were fixed before data; controlled objectives are not human preferences; repeated LLM calls are not independent human subjects. See `AGENTS.md`.
