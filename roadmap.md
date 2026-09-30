# BEFORE THE RECOMMENDATION — LIVE ROADMAP

**Project:** Before the Recommendation: Do Storefront Marketing Cues Shift How AI Shopping Agents Represent Consumer Goals?
**Folder / repo name:** `before-the-recommendation`
**Research status:** Research locked; Phase 1 — BUILD complete and audited; main experiment NOT STARTED
**Hard paper deadline:** 6 October 2026
**Researcher:** Solo undergraduate researcher

---

## How This File Must Be Maintained

This is the living execution roadmap.

- Update it after every meaningful implementation milestone.
- Check off completed tasks with `[x]`; keep incomplete tasks as `[ ]`.
- Record failures, fixes, design changes, and decisions rather than silently changing history.
- Never rewrite the research question or hypotheses after seeing experimental results.
- Every empirical result added here must be traceable to an experiment artifact, log, or analysis output.
- Preserve old decisions in the execution log when they change.
- Keep `project.md` as the authoritative research specification; use this file as the live execution state.

---

# 1. RESEARCH LOCK

### Final title

> **Before the Recommendation: Do Storefront Marketing Cues Shift How AI Shopping Agents Represent Consumer Goals?**

### Research question

> When a consumer's shopping goal is ambiguous, do ordinary marketing cues in product listings alter an AI shopping agent's clarification behavior and operational representation of the consumer's goal, thereby changing recommendation utility?

### Core causal chain

```text
Goal ambiguity × storefront marketing context
        ↓
Agent catalog inspection and clarification policy
        ↓
Question target and simulated-user response
        ↓
Operational preference representation
        ↓
Product ranking and recommendation
        ↓
Utility, regret, constraint violation, and stability
```

### Primary experimental design

```text
2 goal conditions
× 4 marketing conditions
× 2 model families
× 3 repeated runs
```

Goal conditions:
- Ambiguous
- Explicit control

Marketing conditions:
- Neutral
- Scarcity
- Social proof
- Discount framing

Primary domain:
- Laptops

Initial scenario scale:
- Approximately 40 controlled latent profiles/scenario variants

Primary outputs:
- Clarification rate
- Clarification question target
- Preference-Representation Error
- Marketing-induced representation shift
- Recommendation utility
- Regret

Secondary outputs:
- Constraint violations
- Cued-product rank lift
- Evidence usage
- Uncertainty reporting
- Repeat stability
- Failure category

---

# 2. FOUR-PHASE EXECUTION ROADMAP

## PHASE 1 — BUILD

**Objective:** Construct and validate a controlled research instrument.

### Deliverables

- [x] Reproducible scenario generator
- [x] Reproducible synthetic laptop catalog
- [x] Controlled latent-objective generator
- [x] Ambiguous and explicit prompt generator
- [x] Deterministic simulated-user response function/table
- [x] Deterministic utility and regret scorer
- [x] Cue-condition generation with factual utility held constant
- [x] Catalog environment (mock harness passes condition-specific public listings only)
- [x] Agent controller (model-agnostic protocol and deterministic mock-only orchestration)
- [x] Structured-output schema + parser/validator (v1.0.0; strict JSON, field/weight/ranking checks, one validation retry)
- [x] Trace logger (versioned JSONL; raw and derived sections, hidden evaluator section, ordered events, immutable append)
- [x] Failure logger (taxonomy v1 JSONL records)
- [x] Experiment configuration/versioning (versioned JSON config, config SHA-256, generator versions)
- [x] Checkpoint/resume support (SQLite, config-pinned, transactional, explicit recovery transitions)
- [x] Analysis skeleton (descriptive trial rows and summaries only; no inferential statistics)
- [x] Unit tests (49 passing across deterministic layer, parser, trace/failure, checkpoint, metric, analysis skeleton, and interface harness)
- [x] End-to-end pilot (deterministic mock only; not experimental data)

### Pilot exit criteria

Do not start the main experiment until:

- [x] A scenario reproduces exactly
- [x] Utility scoring is unit-tested
- [x] Cue manipulation is isolated
- [x] Utility distributions are balanced across cue arms
- [x] Simulated-user answers are deterministic
- [x] Structured parsing is reliable
- [x] Failures are preserved in raw logs
- [x] One complete trial works end-to-end (also exercised clarification and recovery paths)

### Immediate first implementation target

Build the deterministic layer first:

1. What is the controlled latent consumer objective?
2. Which laptop is optimal under that objective?
3. What answer should the simulated user give to each supported clarification question?
4. What changes between neutral and marketing-cue arms?
5. Is factual utility balanced across cue conditions?

**Do not begin with a production chatbot.**

---

## PHASE 2 — EXPERIMENT + ANALYZE

**Objective:** Generate valid evidence and perform the pre-specified analysis.

### Deliverables

- [ ] Frozen raw dataset
- [ ] Complete balanced core experiment
- [ ] Failure log
- [ ] Clean analysis dataset
- [ ] Primary metrics
- [ ] Primary statistical models
- [ ] Confidence intervals and effect sizes
- [ ] Scenario-level paired bootstrap
- [ ] Required robustness checks
- [ ] Failure taxonomy and counts
- [ ] Paper-ready figures
- [ ] Paper-ready tables

### Required robustness order

1. [ ] Repeated-run stability
2. [ ] Prompt-template variation
3. [ ] Product-order permutation
4. [ ] Model-specific effects
5. [ ] Ambiguous versus explicit comparison
6. [ ] Cue-location sensitivity

### Optional only after the complete core dataset

- [ ] Customer-centered clarification intervention
- [ ] Second catalog
- [ ] Second product domain
- [ ] Small human validation

---

## PHASE 3 — WRITE

**Objective:** Produce the 4,000–5,000-word conference manuscript from observed results.

### Paper structure

- [ ] Title
- [ ] Abstract
- [ ] Introduction
- [ ] Literature review
- [ ] Research gap
- [ ] Conceptual framework
- [ ] Hypotheses
- [ ] Methodology
- [ ] Experimental environment
- [ ] Metrics
- [ ] Statistical analysis
- [ ] Results
- [ ] Failure analysis
- [ ] Robustness
- [ ] Discussion
- [ ] Theoretical implications
- [ ] Managerial implications
- [ ] Ethical implications
- [ ] Limitations
- [ ] Reproducibility
- [ ] Conclusion
- [ ] References

### Writing rule

Write results only from frozen empirical outputs. Never invent numbers, significance, effect sizes, participant findings, or novelty claims.

---

## PHASE 4 — FINALIZE + SUBMIT + PUBLICATION DEVELOPMENT

### Final audit

- [ ] Every numerical result checked against raw/clean analysis files
- [ ] Statistical claims checked
- [ ] Citations verified
- [ ] Novelty language audited
- [ ] Figures/tables checked against source data
- [ ] Equations and notation checked
- [ ] Word/page count checked
- [ ] References checked
- [ ] Author information checked
- [ ] Submission format checked
- [ ] Anonymity requirements checked
- [ ] Plagiarism/self-overlap checked
- [ ] Reproducibility claims checked

### Hostile reviewer pass

Test the manuscript against:

- [ ] Incremental novelty
- [ ] Cue confounding
- [ ] Latent-objective validity
- [ ] Prompt sensitivity
- [ ] Model dependence
- [ ] Repeated-call dependence
- [ ] Metric validity
- [ ] Marketing relevance
- [ ] Generalizability
- [ ] Reproducibility

### Submission package

- [ ] Final PDF
- [ ] Source files
- [ ] Reproducibility appendix/repository
- [ ] Claim → evidence table
- [ ] Submission confirmation archived
- [ ] Publication-development memo

---

# 3. DEADLINE ROADMAP — 30 SEPTEMBER → 6 OCTOBER

## 30 September — Audit, lock, specification

### Target

- [x] Final research lock established
- [x] Define laptop attributes
- [x] Define latent objective classes/vectors
- [x] Define cue treatments
- [x] Define ambiguous/explicit prompts
- [x] Define simulated-user response rules
- [x] Define JSON schema
- [x] Define trace schema
- [x] Define failure taxonomy
- [ ] Write statistical analysis plan
- [x] Create package/configuration structure and Git source revision capture (baseline `028cc0118af599fb96472e4450f301cacff383e9`)

**Exit:** Research Lock + experiment specification.

## 1 October — Build and pilot

- [x] Implement catalog and scenario generator
- [x] Implement latent objective + utility scorer
- [x] Complete Phase 1 unit-test suite (47 tests passing)
- [x] Implement simulated user
- [x] Implement agent controller (mock-only protocol harness; no live model adapter)
- [x] Implement catalog-inspection/clarification flow
- [x] Implement parser, logging, retry logic, checkpointing
- [x] Run end-to-end pilot (mock-only)
- [x] Run small pilot across all core conditions (8 goal × marketing cells; 1 scenario, 1 mock model, 1 repetition per cell)
- [x] Produce parser/failure report

**Exit:** No main experiment until pilot outputs are inspectable and scoring is correct.

## 2 October — Main data generation

- [ ] Freeze code, prompts, catalog, and configuration
- [ ] Tag experiment version
- [ ] Verify model versions and API parameters
- [ ] Run balanced core experiment in checkpointed batches
- [ ] Preserve all raw outputs
- [ ] Rerun only documented technical failures
- [ ] Complete repetitions
- [ ] Generate preliminary summaries

**Exit:** Complete raw core dataset + failure log.

## 3 October — Complete experiment and robustness

- [ ] Validate raw dataset
- [ ] Compute clarification metrics
- [ ] Compute representation metrics
- [ ] Check cue manipulation and utility independence
- [ ] Run repeated-run stability
- [ ] Run prompt-template robustness
- [ ] Run product-order permutation
- [ ] Run model-specific analyses
- [ ] Run cue-location sensitivity if time permits
- [ ] Optional intervention only if core is complete and valid

**Exit:** Frozen analysis dataset + robustness outputs.

## 4 October — Statistics, figures, failure analysis

- [ ] Fit pre-specified statistical models
- [ ] Compute confidence intervals
- [ ] Compute effect sizes
- [ ] Run scenario-level bootstrap
- [ ] Generate clarification figure
- [ ] Generate representation-error figure
- [ ] Generate utility/regret figure
- [ ] Generate cross-model robustness figure
- [ ] Apply failure taxonomy
- [ ] Generate tables

**Exit:** All paper-ready empirical outputs exist.

## 5 October — Write manuscript

- [ ] Introduction
- [ ] Literature review
- [ ] Research gap
- [ ] Conceptual framework
- [ ] Hypotheses
- [ ] Methodology
- [ ] Experimental environment
- [ ] Metrics
- [ ] Statistical analysis
- [ ] Reproducibility
- [ ] Results
- [ ] Failure analysis
- [ ] Robustness
- [ ] Discussion
- [ ] Marketing, ethical, and managerial implications
- [ ] Limitations and conclusion
- [ ] Reference formatting
- [ ] Figure/table integration
- [ ] Word-count and citation checks

**Exit:** Complete 4,000–5,000-word manuscript.

## 6 October — Hostile review and submission

### Morning

- [ ] Check every numerical result against analysis files
- [ ] Check equations and variable definitions
- [ ] Audit novelty language
- [ ] Remove any claim exceeding the evidence

### Midday — ten-objection reviewer pass

- [ ] Novelty
- [ ] Cue confounding
- [ ] Latent-objective validity
- [ ] Prompt sensitivity
- [ ] Model dependence
- [ ] Statistical dependence
- [ ] Metric validity
- [ ] Marketing relevance
- [ ] Generalizability
- [ ] Reproducibility

### Afternoon

- [ ] Fix formatting
- [ ] Verify conference template
- [ ] Verify author information
- [ ] Export final PDF
- [ ] Open and inspect final PDF

### Before deadline

- [ ] Submit
- [ ] Save confirmation
- [ ] Archive source code, configuration, logs, and manuscript

---

# 4. LIVE STATUS

**Current phase:** PHASE 1 — BUILD

**Current milestone:** Phase 1 deterministic instrument and mock-only pilot complete, audited, and pushed

**Current task:** Phase 1 is complete. Stop before the main experiment; no live-model calls or experimental data have been generated.

**Main experiment:** NOT STARTED

**Paper writing:** NOT STARTED

**Submission:** NOT STARTED

## Phase 1 exit audit — 2026-09-30

**Result: PASS for the Phase 1 build and pilot exit criteria.**

- The deterministic smoke report regenerates byte-identically; 40 controlled synthetic objectives and 20 catalog products are reproducible.
- All 40 objective-level cue balance checks pass; maximum per-product utility difference across cue arms is `0.0`.
- The four supported simulated-user clarification targets are deterministic; unsupported targets use the standard uncertainty answer.
- Output schema v1/parser tests cover malformed JSON, duplicate keys, strict field/type checks, catalog membership, normalized weights, and the one-retry limit.
- Trace/failure persistence retains raw responses and retry attempts, separates raw/derived/evaluator-private data, and rejects corrupt or duplicate JSONL trial history.
- Checkpoint tests cover restart, completed-trial skipping, interrupted recovery, documented failed-trial retry, and config/code-revision pinning.
- The deterministic mock completed all 8 goal × marketing cells for one synthetic scenario; final parse status was valid in all 8. One deliberately malformed first response was preserved and recovered once (`invalid_json: 1`).
- The descriptive analysis skeleton emits tidy trial rows and descriptive summaries only; no inferential statistics were run.
- Final command `PYTHONPATH=src python -m unittest discover -s tests -v`: **49 tests passed, 0 failed**.

Pilot scope is infrastructure validation only: one synthetic scenario, one deterministic mock, one repetition per condition cell, and zero external model calls. These outputs are not empirical findings or human preference data. The main experiment remains NOT STARTED.

Committed source revision: `d1f0d0719e0beee5af3feb7fd10118fe36f9109f`.

| Reproducibility artifact | SHA-256 |
|---|---|
| `artifacts/phase1_deterministic_smoke.json` | `C590E29643FAE0D318CA6801CBEFDE60FBBB043BC5D97C7BEFCE2F5121B460CB` |
| `artifacts/phase1_interface_pilot.json` | `471B730142A3C132B9B30E99669713AF05194C11B59F9A734213C08995E67E8C` |
| normalized pilot traces (two runs) | `b7e9f05268a398310a485155d4eb9147fcea0d11e2532302ea3560248b211ffe` |
| pilot failure records (two runs) | `e630ac3e978f49891e8705cea5faf11569fd8904370c996c46e578ecad163ca0` |

## Execution log

| Date | Status | Milestone / decision | Evidence / artifact |
|---|---|---|---|
| 2026-09-30 | LOCKED | Research question, hypotheses, core design, metrics, and four-phase roadmap frozen | `project.md` + research-lock source |
| 2026-09-30 | NEXT | Begin deterministic catalog/objective/simulation/scoring layer | This roadmap |
| 2026-09-30 | COMPLETE | Initial deterministic slice implemented; six unit tests passed, no failures observed | `src/before_recommendation/`, `configs/phase1.json`, `tests/test_deterministic_layer.py`; `python -m unittest discover -s tests -v` |
| 2026-09-30 | COMPLETE | Deterministic foundation integrated: prompts, simulated-user answers, cue overlays, scenario replay, and utility-balance audit | `src/before_recommendation/{prompts,simulated_user,conditions,scenarios}.py`; `scripts/build_deterministic_smoke.py`; `artifacts/phase1_deterministic_smoke.json`; 10/10 unit tests passed after one test correction; report regenerated with identical SHA-256; no trial data generated |
| 2026-09-30 | COMPLETE | Establish Git baseline and source revision capture | Initial local `main` commit `028cc0118af599fb96472e4450f301cacff383e9`; configured identity from authenticated GitHub account; remote `Alyssa-286/Before-the-Recommendation` confirmed empty, no push made; 10/10 tests passed; smoke artifact now records baseline revision. Git emitted a harmless warning because the sandbox cannot read the user-level ignore file; repository `.gitignore` is explicit. | `artifacts/phase1_deterministic_smoke.json`; `.gitignore`; `.gitattributes`; local Git baseline | Add a versioned machine-readable output schema and deterministic parser/validator, with malformed-output cases covered by tests. |

### Update entries

_Add a new row after every meaningful milestone. Never delete historical entries._

| Date/time | Phase | Action | Result | Files/artifacts | Next action |
|---|---|---|---|---|---|
| 2026-09-30 | PHASE 1 — BUILD | Implement versioned catalog, objective generator, and scorer | 6/6 tests passed; no failures or fixes required. Cue balance and simulated-user criteria remain untested because those modules are the next milestone. | `pyproject.toml`; `configs/phase1.json`; `src/before_recommendation/{config,catalog,objectives,evaluator}.py`; `tests/test_deterministic_layer.py` | Add prompt templates, response mapping, and cue overlays; test factual-utility invariance/balance before proceeding to controller. |
| 2026-09-30 | PHASE 1 — BUILD | Complete deterministic foundation and correct the budget interpretation | Final suite: 10/10 passed. First expanded run had 1 failure because the test assumed one explicit-template variant; test now exercises both frozen variants. A manual sample command first omitted `PYTHONPATH`, then hit Windows console encoding on ₹; rerun with `PYTHONPATH=src` and UTF-8 succeeded. During review, ₹70,000 was initially modeled as a hard cap; corrected before any trial to a soft reference with the specified higher-price exception. No generated experiment data were affected. The smoke report regenerated byte-for-byte (SHA-256 `A37BF4A1C60226FECEDA11284639BC77A2C0F80F606D223B06C9DFEA6A046858`). No Git repository was present, so source revision capture remains open. | `configs/phase1.json`; `src/before_recommendation/{config,catalog,objectives,evaluator,prompts,simulated_user,conditions,scenarios}.py`; `tests/test_deterministic_layer.py`; `scripts/build_deterministic_smoke.py`; `artifacts/phase1_deterministic_smoke.json` | Add parser/schema, trace/failure logging, checkpointing, and source revision capture; only then assess remaining pilot gates. |
| 2026-09-30 19:48 IST | PHASE 1 — BUILD | Create the local Git baseline and refresh revision-stamped smoke artifact | `main` root commit `028cc0118af599fb96472e4450f301cacff383e9`; remote checked read-only and is empty; nothing pushed. 10/10 tests passed before baseline. The refreshed deterministic smoke report records the baseline commit and remains a non-experimental artifact. No unresolved test failures. | `.gitignore`; `.gitattributes`; `artifacts/phase1_deterministic_smoke.json`; Git commit `028cc0118af599fb96472e4450f301cacff383e9` | Implement versioned structured output schema and parser; test parse, type, bounds, cross-field, and catalog-ID validation. |
| 2026-09-30 | PHASE 1 — BUILD | Define output schema v1 and strict parser with bounded retry | First targeted run: 9 passed, 1 failed because the test expected JSON `NaN` to reach schema validation; strict JSON correctly rejected it earlier. Corrected the expectation and added a huge-integer overflow case; final parser suite 10/10 and combined suite 20/20 passed. Parser preserves raw values, detects duplicate keys, rejects unknown catalog IDs and inconsistent clarification fields, checks finite [0,1] weights summing within 1e-6, and requests at most one retry for invalid JSON/schema responses. Smoke artifact writer now emits explicit UTF-8/LF; two consecutive builds matched at SHA-256 `3E2A88A6CA04C9924F2B4077FF20B86CD1198706EC940EDE27BD019BB300C9A7`. No model calls or experiment trials. | `schemas/agent_output.v1.schema.json`; `src/before_recommendation/output_parser.py`; `tests/test_output_parser.py`; `scripts/build_deterministic_smoke.py`; `artifacts/phase1_deterministic_smoke.json` | Build typed trace events and append-only JSONL trial logs; define stable event and attempt records and test raw-output retention. |
| 2026-09-30 | PHASE 1 — BUILD | Add versioned JSONL trial trace and failure taxonomy | Trace/failure tests 8/8 passed; full suite 28/28 passed, no failures. Stable trial IDs include conditions, model/prompt versions, repetition, seed, and config digest. JSONL writes are append-only, flushed/fsynced, duplicate trial traces and corrupt history raise errors; raw retry outputs remain verbatim, parsed values/metrics are separate, and evaluator truth occupies a distinct section. Failure taxonomy v1 distinguishes parser, timeout, refusal/rate-limit, interface-order, execution, checkpoint, trace, and scoring failures. No model calls or experiment trials. | `schemas/trace.v1.schema.json`; `src/before_recommendation/{tracing,failures}.py`; `tests/test_tracing.py` | Add durable checkpoint/resume keyed by deterministic trial ID and config digest; exercise interrupted batches, completed-trial skipping, duplicate protection, and changed-config behavior. |
| 2026-09-30 | PHASE 1 — BUILD | Add transactional, config-pinned checkpoint/resume | Checkpoint tests 6/6 passed; full suite 34/34 passed, no failures. Register/claim/complete/fail transitions are transactional; completed IDs are skipped on restart, interrupted `running` rows require explicit recovery, failed rows require documented requeue reason, and a changed config digest is rejected. No trial data or model calls. | `src/before_recommendation/checkpoint.py`; `tests/test_checkpoint.py`; SQLite test artifacts only in temporary directories | Define the interface protocol and deterministic mock, then test one clarification and one no-clarification trial through parse, score, trace, and checkpoint. |
| 2026-09-30 | PHASE 1 — BUILD | Implement model-agnostic public interface and mock orchestration | First test discovery failed at import because `GoalCondition` is defined in `prompts.py`, not `conditions.py`; imports were corrected. Interface tests then passed 6/6 and full suite 43/43 passed. Clarification and no-clarification paths, unsupported-target uncertainty, catalog-before-question ordering, raw retry preservation, deterministic scoring, JSONL trace, and checkpoint completion all pass. Hidden objective is only available to the research harness and evaluator. No external model or main experiment. | `src/before_recommendation/{agent_protocol,mock_agent,interface_runner}.py`; `src/before_recommendation/evaluator.py`; `tests/{test_interface_runner,test_representation_metric}.py` | Run the small mock-only interface pilot twice, compare normalized traces, and write the parser/failure report artifact. |
| 2026-09-30 20:21 IST | PHASE 1 — BUILD | Complete the deterministic mock-only interface pilot across all core condition cells | Expanded full suite: 47/47 passed. Pilot script ran its 8-cell mock batch twice and matched normalized trace/failure records; two separate script invocations also produced the same report SHA-256 `08F6662C813DE11F7AB2F5B62C1E3C0F48A72DB8553C8EB9370C62F01EC217F7`. All 8 mock trials completed with valid final outputs; one injected malformed first response was retained and recovered once. Failure report records `invalid_json: 1`. The analysis skeleton creates descriptive rows only. Pilot uses 1 synthetic scenario, 1 mock model, 1 repetition per cell; 0 external model calls. Source revision will be refreshed after implementation commit. | `scripts/run_interface_pilot.py`; `artifacts/phase1_interface_pilot.json`; `src/before_recommendation/analysis.py`; `tests/test_analysis.py`; full `tests/` suite | Commit the validated code and roadmap, regenerate both reports at that revision, run the final full suite, perform Phase 1 exit audit, then push. |
| 2026-09-30 20:30 IST | PHASE 1 — BUILD | Final clean-revision audit and reproducibility comparison | Source revision `d1f0d0719e0beee5af3feb7fd10118fe36f9109f`; final suite 49/49 passed. Smoke and interface report each regenerated twice with identical SHA-256 values. Eight mock condition cells completed; the expected injected invalid-JSON response was preserved and recovered once. All Phase 1 pilot exit criteria pass; no external models or main experiment. | `artifacts/phase1_deterministic_smoke.json`; `artifacts/phase1_interface_pilot.json`; `schemas/agent_output.v1.schema.json`; `schemas/trace.v1.schema.json`; full `tests/` suite; source commit `d1f0d0719e0beee5af3feb7fd10118fe36f9109f` | Push the audited Phase 1 build to the verified empty `main` remote. |
| 2026-09-30 20:33 IST | PHASE 1 — BUILD | Push audited Phase 1 build after exit audit | Push succeeded to `origin/main`; upstream tracking configured. The pushed tree contains the audit and both revision-stamped reproducibility artifacts. The remote was empty before the authorized push. No main experiment or external model calls. | GitHub `Alyssa-286/Before-the-Recommendation`, branch `main`; commit `725d3c0` | Phase 1 complete. Stop before the main experiment. |

---

# 5. RESEARCH INTEGRITY CHECKPOINT

Before progressing from any phase, verify:

- No fabricated results
- No hidden failed runs
- No post-hoc hypothesis rewriting
- Synthetic profiles are not described as humans
- Standard metrics are not claimed as novel inventions
- No hidden chain-of-thought is required
- No dramatic-only failure cherry-picking
- No silent manual correction
- LLM calls are not treated as independent human participants
- Observed results, interpretations, expectations, and future work remain distinct

---

# 6. CODEx OPERATING RULE

When working in this repository, read `project.md` before changing research-critical code and read `roadmap.md` before beginning a new phase or milestone.

After completing a meaningful milestone:

1. Run relevant tests.
2. Record what changed.
3. Record failures and fixes honestly.
4. Update this roadmap.
5. Leave the repository in a reproducible state.

Do not broaden the research design merely because an interesting extension appears. Core completion has priority over optional extensions.
