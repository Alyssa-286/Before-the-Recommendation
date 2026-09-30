# BEFORE THE RECOMMENDATION — LIVE ROADMAP

**Project:** Before the Recommendation: Do Storefront Marketing Cues Shift How AI Shopping Agents Represent Consumer Goals?
**Folder / repo name:** `before-the-recommendation`
**Research status:** Research locked; Phase 1 — BUILD
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
- [ ] Catalog environment
- [ ] Agent controller
- [ ] Structured-output schema + parser/validator
- [ ] Trace logger
- [ ] Failure logger
- [x] Experiment configuration/versioning (versioned JSON config, config SHA-256, generator versions)
- [ ] Checkpoint/resume support
- [ ] Analysis skeleton
- [ ] Unit tests
- [ ] End-to-end pilot

### Pilot exit criteria

Do not start the main experiment until:

- [x] A scenario reproduces exactly
- [x] Utility scoring is unit-tested
- [x] Cue manipulation is isolated
- [x] Utility distributions are balanced across cue arms
- [x] Simulated-user answers are deterministic
- [ ] Structured parsing is reliable
- [ ] Failures are preserved in raw logs
- [ ] One complete trial works end-to-end

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
- [ ] Define JSON schema
- [ ] Define trace schema
- [ ] Define failure taxonomy
- [ ] Write statistical analysis plan
- [x] Create package/configuration structure (source revision capture still needs a Git repository before experiment freeze)

**Exit:** Research Lock + experiment specification.

## 1 October — Build and pilot

- [x] Implement catalog and scenario generator
- [x] Implement latent objective + utility scorer
- [ ] Complete Phase 1 unit-test suite (deterministic layer currently has 10 passing tests)
- [x] Implement simulated user
- [ ] Implement agent controller
- [ ] Implement catalog-inspection/clarification flow
- [ ] Implement parser, logging, retry logic, checkpointing
- [ ] Run end-to-end pilot
- [ ] Run small pilot across all core conditions
- [ ] Produce parser/failure report

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

**Current milestone:** Deterministic foundation complete and validated; controller/pilot prerequisites remain

**Current task:** Implement the structured output schema/parser, trace and failure logging, and checkpointing; then run the deterministic interface pilot. Do not start the agent controller or main experiment before the remaining Phase 1 gates pass.

**Main experiment:** NOT STARTED

**Paper writing:** NOT STARTED

**Submission:** NOT STARTED

## Execution log

| Date | Status | Milestone / decision | Evidence / artifact |
|---|---|---|---|
| 2026-09-30 | LOCKED | Research question, hypotheses, core design, metrics, and four-phase roadmap frozen | `project.md` + research-lock source |
| 2026-09-30 | NEXT | Begin deterministic catalog/objective/simulation/scoring layer | This roadmap |
| 2026-09-30 | COMPLETE | Initial deterministic slice implemented; six unit tests passed, no failures observed | `src/before_recommendation/`, `configs/phase1.json`, `tests/test_deterministic_layer.py`; `python -m unittest discover -s tests -v` |
| 2026-09-30 | COMPLETE | Deterministic foundation integrated: prompts, simulated-user answers, cue overlays, scenario replay, and utility-balance audit | `src/before_recommendation/{prompts,simulated_user,conditions,scenarios}.py`; `scripts/build_deterministic_smoke.py`; `artifacts/phase1_deterministic_smoke.json`; 10/10 unit tests passed after one test correction; report regenerated with identical SHA-256; no trial data generated |

### Update entries

_Add a new row after every meaningful milestone. Never delete historical entries._

| Date/time | Phase | Action | Result | Files/artifacts | Next action |
|---|---|---|---|---|---|
| 2026-09-30 | PHASE 1 — BUILD | Implement versioned catalog, objective generator, and scorer | 6/6 tests passed; no failures or fixes required. Cue balance and simulated-user criteria remain untested because those modules are the next milestone. | `pyproject.toml`; `configs/phase1.json`; `src/before_recommendation/{config,catalog,objectives,evaluator}.py`; `tests/test_deterministic_layer.py` | Add prompt templates, response mapping, and cue overlays; test factual-utility invariance/balance before proceeding to controller. |
| 2026-09-30 | PHASE 1 — BUILD | Complete deterministic foundation and correct the budget interpretation | Final suite: 10/10 passed. First expanded run had 1 failure because the test assumed one explicit-template variant; test now exercises both frozen variants. A manual sample command first omitted `PYTHONPATH`, then hit Windows console encoding on ₹; rerun with `PYTHONPATH=src` and UTF-8 succeeded. During review, ₹70,000 was initially modeled as a hard cap; corrected before any trial to a soft reference with the specified higher-price exception. No generated experiment data were affected. The smoke report regenerated byte-for-byte (SHA-256 `A37BF4A1C60226FECEDA11284639BC77A2C0F80F606D223B06C9DFEA6A046858`). No Git repository was present, so source revision capture remains open. | `configs/phase1.json`; `src/before_recommendation/{config,catalog,objectives,evaluator,prompts,simulated_user,conditions,scenarios}.py`; `tests/test_deterministic_layer.py`; `scripts/build_deterministic_smoke.py`; `artifacts/phase1_deterministic_smoke.json` | Add parser/schema, trace/failure logging, checkpointing, and source revision capture; only then assess remaining pilot gates. |

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
