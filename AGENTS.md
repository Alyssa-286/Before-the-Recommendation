# Codex Project Instructions

This repository is a time-constrained research project. The authoritative research specification is `project.md`. The living execution state is `roadmap.md`.

Before doing research-critical implementation:
1. Read `project.md` in full.
2. Read the current relevant sections of `roadmap.md`.
3. Preserve the locked causal design unless a reproducibility, validity, or implementation defect requires a documented change.

Research integrity is mandatory:
- Never fabricate results, statistics, citations, or novelty.
- Never hide failed runs.
- Never silently change hypotheses after observing results.
- Treat synthetic latent objectives as controlled evaluation targets, not real human preferences.
- Do not use hidden chain-of-thought as an experimental observable.
- Preserve raw outputs and technical failures.
- Keep deterministic evaluator logic separate from the agent.
- Do not treat repeated LLM calls as independent human subjects.

Execution priority:
- Finish the deterministic catalog/objective/simulated-user/scoring layer first.
- Validate cue isolation and utility balance before connecting the agent controller.
- Build reproducible logging, parsing, checkpointing, and tests.
- Do not start the main experiment until the Phase 1 pilot exit criteria in `roadmap.md` pass.
- Optional intervention, second catalog/domain, and human validation come only after the core study is complete.

After every meaningful milestone, update `roadmap.md` with the actual result, artifact paths, failures/fixes, and next action.
