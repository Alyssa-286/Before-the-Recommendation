# Final Report

## Project status
- Phase 1 (build): complete.
- Phase 2 (experiment + analysis): core 1,920/1,920 executed; robustness: template 311 of 320 runs valid; audit passed; order 303 of 320 runs valid; audit passed; cue location not run.
- Phase 3 (write): manuscript rendered from computed results (4953 words excluding references and tables).
- Phase 4 (finalize): final audit in `artifacts/final_audit.md`; open items are researcher actions (author details, official conference format check, portal submission).

## Model access
Candidates: OpenAI (no credits), Google Gemini, Groq (Free plan, insufficient daily tokens), Mistral. Selected: `gemini-3.1-flash-lite` (Google) and `ministral-14b-2512` (Mistral) — the lowest-cost eligible model-family pair under the predefined experimental constraints with a strict zero budget. Gemini credentials used: GEMINI_API_KEY_2, _3, _5 (FreeTier confirmed, 500 requests/day/project); GEMINI_API_KEY excluded (tier unconfirmed); GEMINI_API_KEY_4 rejected (HTTP 403). Cost: zero.

## Experiment
Planned 1,920; valid 1,881 (98.0%); terminal failures 39 (Gemini 0, Ministral 39); parser retries Gemini 5, Ministral 4; technical re-runs 0/0; interruption requeues 16/6; provider calls 5,409; tokens 6,966,711.

## Data quality
Audit: 24 checks passed; leakage scan of 5,409 model-visible requests clean; metrics independently recomputed; final validation: see artifacts/final_validation.json.

## Statistics (ambiguous goal, commercial − neutral; pooled, equal model weights)
- Clarification -0.054 (95% CI -0.070 to -0.039) (Holm p < 0.001)
- ΔD -0.001 (95% CI -0.006 to +0.004) (Holm p = 0.729)
- Utility -0.006 (95% CI -0.010 to -0.003) (Holm p < 0.001); regret +0.006 (95% CI +0.003 to +0.010)
- H1 ambiguous − explicit D +0.095 (95% CI +0.069 to +0.119)
- Verdicts: H1 supported (pooled and in both model families); H2 not supported (95% intervals include zero, pooled and per model); H3 not supported (the moderation contrast includes zero); H4 not supported in the stated direction; the observed dissociation runs the other way: utility changed while representation error did not; H5 exploratory; under ambiguous goals the interval includes zero

## Outputs
Figures: `outputs/figures/fig1…fig8`; tables: `outputs/tables/`; manuscript: `manuscript/paper.md|.docx|.pdf`; submission package: `submission/`.

## Reproducibility
Repository commit at build `4ccc396ada90f7294cac2fc07a8b843b34096485`; execution revision `33bfa10`; core config SHA-256 `072fb8f50a64984a370f41bb6b7311a7823ba6781893c84a20099fba0742740a`; catalog seed 20260955; bootstrap seed 20260930.

## Publication development
`artifacts/publication_development_memo.md`. Strongest limitation: synthetic environment with a single-dimension simulated user. Highest-value next study: answerable-dialogue protocol with multiple cue wordings and real product feeds.

## Remaining blockers
Researcher-only: author information, verification against the official conference call, and portal submission.
