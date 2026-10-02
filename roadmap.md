# BEFORE THE RECOMMENDATION — LIVE ROADMAP

**Project:** Before the Recommendation: Do Storefront Marketing Cues Shift How AI Shopping Agents Represent Consumer Goals?
**Folder / repo name:** `before-the-recommendation`
**Research status:** Research locked; Phase 1 complete; Phase 2 access probes and 32-run live pilot complete; core freeze blocked at quota gate; main experiment NOT STARTED
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
- [x] Write and freeze the pre-data statistical analysis plan (`analysis/analysis_plan.md`, v1.0.0)
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

**Current phase:** PHASE 2 — EXPERIMENT + ANALYZE (live pilot complete; freeze blocked at cost/quota gate)

**Current milestone:** Provider access validated, lowest-cost eligible pair computed, 32-run live pilot passed infrastructure checks (2026-10-01).

**Current task:** Core experiment (1,920 runs) executing from the frozen configuration; then data-quality audit, analysis, robustness, manuscript.

**Main experiment:** NOT STARTED

**Paper writing:** NOT STARTED

**Submission:** NOT STARTED

## Phase 2 core execution log — 2026-10-02

- Mistral core arm complete: 960/960 executed (921 valid, 39 terminal). Review (`artifacts/mistral_core_failure_review.json`): 35 plain-text responses without a tool call, 1 second clarification, 3 schema-invalid after the parser retry; 0 provider failures; none eligible for the frozen technical re-run; all retained. Mistral robustness datasets collected (template 151/160, order 143/160, cue location 155/160 valid).
- Detached runner processes ended twice without completion records (machine sleep/session end); checkpoints and raw JSONL intact each time; relaunched pinned to `33bfa10` with stale-lock removal after confirming no live process. Gemini core at 645/960 after the 2026-10-02 quota window; resumes at the 07:05Z reset (projected completion ~08:00Z 2026-10-03).
- `GEMINI_API_KEY_4` (researcher-reported new project): one tiny test request returned HTTP 403 "Your project has been denied access"; not added to the pool; no further requests.
- `GEMINI_API_KEY_5` (researcher-reported new project): one tiny test request returned HTTP 200 from `gemini-3.1-flash-lite` while keys 2/3 were at their daily limit (hence a different project). Added as an execution credential for the same Gemini model via `run_experiment.py --extra-credential` (scripts only; frozen `src` unchanged); runner resumed from the existing checkpoint at 645/960 pinned to `33bfa10`. Free-tier status is confirmed only when its first FreeTier quota response is logged.

## Phase 2 core execution log — 2026-10-01

**Status: CORE RUNNING (checkpointed, detached). No design change.**

- Core launched 11:55Z at freeze commit `33bfa10`. The first runner process stopped when the agent session ended at 492 completed traces; raw JSONL integrity verified (0 malformed lines). Resumed 18:19Z pinned to `33bfa10` (no `src`/`configs`/`schemas`/`analysis` change since the freeze, verified by `git diff`). In-flight trials were requeued by the checkpoint and re-run as attempt 2 (attempt-1 raw I/O preserved). To survive future session ends, the runner was relaunched 18:26Z as a detached OS process with a single-runner lock file; robustness stages are chained by detached orchestrators (`scripts/orchestrate_robustness.py`, `logs/orchestrator.log`) that start only after each family's core arm completes.
- **Gemini daily quota confirmed:** HTTP 429 quotaId `GenerateRequestsPerDayPerProjectPerModel-FreeTier`, quotaValue **500** per project; resets at midnight Pacific (07:00 UTC). Two free projects give 1,000 requests/day; observed ~2.96 requests per Gemini trial. The pool suspends an exhausted credential until reset (`credential_suspended_daily_quota` events). Projected Gemini core completion: ~2026-10-03 08:00Z; Gemini robustness (480 trials) thereafter in plan order, expected to complete ~2026-10-05. Mistral (Free mode, 30 RPM, no daily cap observed) completes its core arm within hours, then its robustness stages.
- Interim validity monitoring only (no outcome inspection): Gemini 0 terminal failures in the first 227; Mistral terminal failures are interface-contract violations (response without exactly one tool call), preserved and counted.

## Phase 2 free-route capacity, selection and experiment freeze — 2026-10-01

**Status: EXPERIMENT FROZEN (`artifacts/experiment_freeze.json`); core run starting. Budget: INR 0.**

- New credentials (names only): `GEMINI_API_KEY_2`, `GEMINI_API_KEY_3`, `MISTRAL_API_KEY`, `MISTRAL_API_KEY_2`, `GROQ_API_KEY_2` (GroqCloud `gsk_` format, not xAI).
- Capacity audit (`artifacts/credential_capacity_audit.json`, `artifacts/gemini_tier_probe.json`; tiny bounded calls): Gemini keys 2 and 3 returned HTTP 429 with quotaId `GenerateRequestsPerMinutePerProjectPerModel-FreeTier` (quotaValue 15) and behave as separate projects; `GEMINI_API_KEY` accepted 30 burst calls without a FreeTier response, so its free status is unconfirmed and it is EXCLUDED. Mistral Free mode: `ministral-14b` 30 RPM / 937,500 TPM and `ministral-8b` 188 RPM / 625,000 TPM; `mistral-small`/`medium` have 0 RPM; both Mistral keys decrement the same counters (one shared workspace pool). Groq keys are separate Free orgs (independent counters), each 200K TPD. Official Gemini docs: limits are per project; no fetched term prohibits separate projects the researcher controls.
- Mistral selection probe (`artifacts/mistral_selection_probe.json`, not research data): ministral-14b-2512 and ministral-8b-2512 both 4/4 valid, 0 parser retries, 0 leakage; 14b selected on lower tokens/trial (4,006 vs 4,339).
- **Frozen pair** (`artifacts/model_selection.json` v2): Google `gemini-3.1-flash-lite` (pool `GEMINI_API_KEY_2`, `GEMINI_API_KEY_3`) + Mistral `ministral-14b-2512` (`MISTRAL_API_KEY`). Uniform settings: provider-default temperature, 4,096 max output tokens, 120 s timeout.
- Added `CredentialPoolTransport` (per-credential pacing; per-minute 429 delays a credential; daily-quota 429 suspends it until reset; secrets redacted; variable names logged per request). Config hash now excludes credential variable names. 85 tests pass.
- Final pilot `pilot_v2` (`artifacts/live_pilot_v2_summary.json`, not research data): Gemini 16/16 valid, Mistral 15/16 valid; 0 parser retries; 0 leakage; all ordering/cue/utility-invariance checks pass.
- Freeze records environment hashes, prompts/tools, file SHA-256s, model configs, per-model live config hashes (Gemini `6fe40d8a...`, Mistral `2fe18e4b...`), retry/exclusion rules, robustness stages (ambiguous goal, 40 scenarios x 4 arms x 1 rep per model per check, frozen pre-data), pre-data deviations, and a capacity plan (~2,840 Gemini and ~3,040 Mistral requests incl. 10% reserve; ~118 min / ~127 min at paced rates if daily quotas allow).

| 2026-10-01 | PHASE 2 — FREEZE | Capacity audit, Mistral selection, pilot v2, experiment freeze | Free routes verified for Gemini (2 projects) and Mistral; pilot v2 passed; freeze written before core data. | `artifacts/{credential_capacity_audit,gemini_tier_probe,mistral_selection_probe,live_pilot_v2_summary,model_selection,experiment_freeze}.json` | Run the 1,920-run core in checkpointed batches. |

## Phase 2 validity and free-quota gates — 2026-10-01

**Status: SCIENTIFIC-VALIDITY GATE PASSED (offline); FREE-QUOTA GATE FAILED with current keys. Main experiment NOT STARTED. Budget constraint from researcher: strictly INR 0 (no billing, upgrades, credits, paid usage, or extra accounts).**

- **Catalog audit:** no scoring or normalization bug (independent recomputation matches 40/40 optima); objective weights span 0.07-0.60 per dimension. Cause of the single optimum: the Phase-1 catalog generator draws all attributes i.i.d. with no price-attribute trade-off; under seed 20260930 `LumaBook_P16` Pareto-dominates 15/19 products and is optimal on 98.2% of the Dirichlet(1) weight simplex. Across 1,000 generator seeds, a median of only 3 distinct optima occurs (single optimum in 10.9%). Classified as a construct-validity defect of the catalog generator.
- **Correction (catalog-acceptance-v1.0.0):** 10 acceptance criteria were committed first (`349e932`, `src/before_recommendation/environment_diagnostics.py`), before any search: >=5 distinct optima, max single-optimum share <=0.30, >=4 distinct class-modal optima, simplex max share <=0.50, <=10 products Pareto-dominated by one product, cued-optimum share in [0.10, 0.40], cued mean utility percentile in [0.35, 0.65], cued price gap <= INR 10,000, identical factual utility across arms, full profile-class coverage. Deterministic seed search (base seed upward) rejected 25 seeds and accepted catalog seed 20260955 (`c962e51`; `configs/core_v2.json`; `artifacts/environment_seed_search.json`). Accepted catalog: 5 distinct optima (max 12/40), simplex max 0.252, max dominated-by-one 1, cued-optimum share 0.10, cued percentile 0.552, price gap INR 2,850, factual utility identical. Attribute generator, objectives, cue seed, prompts and hypotheses unchanged; `configs/phase1.json` preserved. Tests: Phase-1 catalog fails, core_v2 passes, objectives/cue seed preserved, exact reproduction, cues never alter facts.
- **Token audit** (`artifacts/token_demand_audit.json`): in the v1.0 pilot the catalog tool result (~4,145 chars of JSON) was re-sent on every later call and dominated input (input = 87-90% of tokens); `sum` parser retries added ~1 call per affected trial.
- **Instrument v1.2.0 (pre-freeze, `c967097`):** lossless pipe-table catalog (72% fewer chars; all attributes and cue labels retained); the model no longer sees the arm name (`marketing_condition`) or the internal catalog fingerprint; concise-output guidance (<=5 evidence phrases, <=2-sentence explanation); weight-sum constraint stated. Mistral adapter added as a free-tier contingency. 82 tests pass.
- **Token measurement** (8 Groq gpt-oss-20b trials, corrected catalog, infrastructure only, `data/token_measurement/`): 7/8 valid (1 interface-contract failure preserved), 0 parser retries, 2.25 calls, 2,042 input + 641 output = 2,683 tokens per trial, 0 leakage findings.
- **Free-quota feasibility** (`artifacts/free_quota_feasibility.json`): gpt-oss arm needs ~2.58 M tokens; Groq Free allows 200 K/day, so ~12.9 days versus a ~3.7-day collection window (about 277 trials). Gemini free-tier limits and billing status are visible only in AI Studio (unverified). OpenAI: no credits. Cerebras: requires a payment method (trial credits only). Mistral: official docs state Free mode needs no credit card; numeric limits visible only in its Admin panel; `MISTRAL_API_KEY` not configured. OpenRouter/GitHub Models/NVIDIA NIM numeric free limits could not be verified from official pages.
- **Exact decision needed (researcher):** (1) read the Gemini project tier and `gemini-3.1-flash-lite` free RPD/TPD in AI Studio and confirm no billing is linked; (2) either create a free Mistral API key (no card) and add `MISTRAL_API_KEY` to `.env`, so the pair becomes Google Gemini + Mistral subject to verified limits, or explicitly approve a documented design deviation. No core runs until both gates pass.

| 2026-10-01 | PHASE 2 — VALIDITY/QUOTA GATES | Catalog audit and correction; token audit; v1.2 instrument; Groq token measurement; free-provider audit | Validity gate passed offline (seed 20260955); free-quota gate failed with current keys (Groq TPD binding, Gemini unverified). No core data. | `artifacts/{environment_seed_search,token_demand_audit,free_quota_feasibility}.json`; `configs/core_v2.json`; `data/token_measurement/` | Researcher: Gemini tier check and a free Mistral key, or an approved deviation. |

## Phase 2 live access, selection and pilot — 2026-10-01

**Status: PILOT PASSED (infrastructure); COST/QUOTA GATE FAILED; experiment freeze NOT created; main experiment NOT STARTED.**

- Credentials: `OPENAI_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY` all SET via the repository `.env` loader (`src/before_recommendation/runtime_config.py`); `.env` is git-ignored; values never printed or committed (staged-diff scans clean before every commit). GitHub push works again (`98c8ea4..e8a6a75`).
- Discovery fix: Groq's edge returned Cloudflare `error code: 1010` to urllib's default User-Agent; an explicit research User-Agent was added to discovery and the adapter transport. Discovery then listed 127 OpenAI, 50 Gemini and 11 Groq model IDs (`artifacts/model_access_matrix.json`).
- Pricing verified from official pages on 2026-10-01 (OpenAI `developers.openai.com/api/docs/pricing`, Gemini `ai.google.dev/gemini-api/docs/pricing`, Groq `console.groq.com/docs/models` and `/docs/rate-limits`).
- Access probes (2 infrastructure trials per candidate; `artifacts/live_access_probe.json`, raw `data/access_probes/`; NOT research data): `gpt-5-nano-2025-08-07` and `gpt-4.1-nano-2025-04-14` returned HTTP 429 `insufficient_quota`/`credit_balance_exhausted` (no OpenAI API credits); `gemini-2.5-flash-lite` returned HTTP 404 "no longer available to new users"; `gemma-4-26b-a4b-it` was 0/2 protocol-compliant with ~88 s latency; `gemini-3.1-flash-lite`, `openai/gpt-oss-20b` (Groq) and `qwen/qwen3.8-27b` (Groq) completed the protocol. Leakage check: 0 findings for all candidates. An interrupted first probe run (quota 429s being re-sent) is preserved in `data/superseded/access_probes_run1_interrupted/`; the transport no longer re-sends quota-exhaustion 429 bodies.
- Selection (`artifacts/model_selection.json`, provisional): lowest-cost eligible model-family pair under the predefined experimental constraints = Google `gemini-3.1-flash-lite` + OpenAI open-weight `openai/gpt-oss-20b` (served by Groq). Projected paid cost for 2 x 960 core runs from pilot measurements is about $2.51 (Gemini $2.09, gpt-oss $0.43) versus $14.8-16.5 for pairs involving Qwen.
- New instrumentation (offline-tested; 77 tests pass): `experiment_runner.py` (checkpointed batches, per-model pacing, logged transport re-sends for 429/5xx without model output, exactly one full technical re-run after a provider failure with attempt-numbered preserved files; refusals/protocol/parser failures never re-run), `leakage.py` (automated isolation check over every model-visible request), `dataset.py` (analysis rows and pre-specified taxonomy operational rules, written before any core data), `statistics.py` (plan v1.0.0 matched contrasts, 10,000-draw scenario bootstrap seed 20260930, clustered factorial models, Holm), and `ProtocolVariant` for robustness (alternate template, product-order permutation, cue relocation; core hash unchanged; unit-tested).
- 32-run live pilot (`artifacts/live_pilot_summary.json`, raw `data/pilot/`, code `d052ea0`; NOT research data): Gemini 16/16 valid; gpt-oss 14/16 valid (1 terminal schema failure after the permitted retry; 1 plain-text response without a tool call). All infrastructure checks pass: catalog exposed only via tool result, inspection before every clarification, cue labels only in commercial arms, clarification and simulated-user path exercised, traces complete (32/32), failures preserved, 0 leakage findings, factual utility invariant across arms. Observed per trial: Gemini 3.19 calls, 5,282 input / 569 output tokens; gpt-oss 2.69 calls, 3,703 / 551 tokens.
- **Pilot-found instrument defect (fixed before any freeze):** parser retries occurred in 11/16 Gemini and 7/16 gpt-oss pilot trials, all with issue code `sum`: the `submit_recommendation` tool never told the model that weights must sum to 1, although the parser enforces it. The tool description now states the constraint (controller v1.1.0). Outputs are never normalized or repaired. This changes the config hash; a re-pilot is required before freeze.
- **Cost/quota gate FAILED** (`artifacts/cost_quota_gate.json`): the Groq organization is on the Free plan (response headers: 1,000 requests/day, 8,000 tokens/min; documented 200,000 tokens/day for gpt-oss-20b). The core needs about 4.1 M gpt-oss tokens, i.e. about 20 days of free daily quota. The Gemini tier is only visible in AI Studio (unverified); about 3,060 calls are needed. OpenAI has no API credits. The design was not reduced.
- **Catalog-dominance finding** (`artifacts/catalog_dominance_audit.json`): `LumaBook_P16` (INR 37,000; quality 100, durability 96, sustainability 93) is the optimal feasible product for all 40 objectives; the five cued products are one seeded draw reused in every commercial arm (none optimal; 3 of 5 above INR 70,000). Factual-utility equality across arms still holds, so the cue manipulation remains clean, but regret has a ceiling structure and cued-product rank lift is tied to one product set. Requires a researcher decision (keep the frozen Phase-1 catalog and report the limitation, or authorize a documented pre-data catalog revision).
- **Exact next action (researcher):** upgrade Groq to the Developer plan (or add OpenAI API credits), confirm or enable the Gemini billing tier, and decide the catalog question. Then: re-pilot with controller v1.1.0, freeze, run the core.

| 2026-10-01 | PHASE 2 — ACCESS/SELECTION/PILOT | Probes, selection, 32-run pilot, cost gate | Pilot passed infrastructure checks; weight-sum instruction defect found and fixed pre-freeze; quota gate failed (Groq Free plan); catalog dominance finding recorded. No core data. | `artifacts/{model_access_matrix,live_access_probe,model_selection,live_pilot_summary,cost_quota_gate,catalog_dominance_audit}.json`; `data/{access_probes,pilot}/` | Researcher: quota/billing and catalog decision; then re-pilot and freeze. |

## Phase 2 preflight — 2026-09-30

**Status: BLOCKED at Checkpoint A; main experiment NOT STARTED.**

- Read `project.md`, `roadmap.md`, and `AGENTS.md` completely before edits. Inspected the clean Phase 1 baseline at `015df787ca22fd3ce2cda9557e74b50b7884dc7d` and its deterministic catalog, objectives, scorer, cue overlays, scenario view, mock protocol, parser, trace, failure, and checkpoint implementation.
- Model-access inventory: `artifacts/phase2_model_access.json`. No OpenAI, Anthropic, or Google API key was present in process/user/machine environment scopes. Codex session is authenticated through ChatGPT (`gpt-6-luna` in local Codex config), but has no OpenAI Platform API key or research-adapter endpoint. AWS CLI is present with zero configured profiles; the AWS SSO cache path was not inspectable due a Windows access-denied response. No local inference server was found.
- No provider/model exact ID is selected; no live probe was attempted; zero external model calls were made. Checkpoint A is not passed. The suggested 32-run live pilot, model configuration freeze, full experiment freeze, and main-run budget estimate are blocked until two actual provider families and exact model IDs are accessible.
- Pre-data analysis plan frozen at `analysis/analysis_plan.md` v1.0.0 (SHA-256 `19313BAB9808430735BAA67B0C8AEF3F26BF4C9A8D2D4A7CFD27C088DBEB65DD`). It specifies the 1,920-run core count, paired commercial-versus-neutral ambiguous-goal primary contrast, five reported primary outcomes/four distinct primary contrasts, fixed model-family effects, 10,000 scenario-cluster bootstrap replicates (seed `20260930`), failure/missingness rules, audit gate, and robustness order. This is the analysis-plan freeze only; it is not the experiment freeze.
- Environment reconnaissance command issue: the first optional Python package check raised `ModuleNotFoundError` while probing the nested `google.genai` module because its parent package was absent. The probe was corrected to check the parent before the child; the corrected inventory found no OpenAI, Anthropic, Google GenAI, boto3, NumPy, pandas, SciPy, statsmodels, or Matplotlib packages. No repository files or data were changed by the failed check.
- Initial preflight next action was to build adapters/controller after access review; that offline implementation milestone is now complete. The remaining next action is to make two budget-approved research API families and exact model IDs accessible, then run the separately logged live access pilot and freeze model-specific settings before any core trial.

## Phase 2 offline adapter/controller milestone — 2026-09-30

**Status: OFFLINE IMPLEMENTATION PASS; LIVE MODEL ACCESS AND PILOT BLOCKED.**

- Added `src/before_recommendation/model_adapters.py`: standard-library HTTPS adapters for OpenAI Chat Completions and Anthropic Messages, typed provider-neutral messages/tool calls, one request per turn, no automatic retries or tool execution, explicit model/settings metadata, sanitized provider failures, and no credential values in returned metadata or logs.
- Added `src/before_recommendation/live_controller.py`: a frozen fixed-template request; first-call-only `inspect_catalog`; catalog facts and cue labels delivered only as a tool result; one tool call per model response; at most one deterministic controller-inserted clarification answer; final `submit_recommendation`; strict causal-order checks; one parser retry maximum; per-turn append/fsync raw I/O records with request payload, response bytes (base64), readable response, hashes, timestamps, request IDs, latency, and usage; headers and API keys are excluded.
- Added `schemas/agent_output.v2.schema.json` and `src/before_recommendation/live_output.py`. The model-owned output includes only preference weights, ranking, evidence, uncertainty, and explanation. Catalog inspection, clarification decision/question/target, and simulated answer remain controller/protocol records. The Phase 1 v1 schema remains unchanged.
- The controller rechecks factual-utility balance across all four cue arms before a model call, stores the diagnostics under evaluator-private trace data, and exposes only the selected arm's factual records/cue labels to the model. Trial config hashes pin the Phase 1 config, model settings, analysis-plan bytes/version, frozen prompt/tool/schema contract, and protocol limits; live trials require a committed code revision in their identity/checkpoint records.
- Updated `src/before_recommendation/analysis.py` to flatten v2 output and controller-recorded clarification metrics while retaining Phase 1 compatibility. Recovered invalid submissions remain both in parser attempts and the failure log as recoverable failures.
- Added `tests/test_live_model_path.py` for both provider request formats, strict schemas, secret exclusion, missing credentials/no network, preserved 429 bodies, config hash stability, duplicate tool-argument rejection, causal tool order, no parallel calls, compound-question uncertainty, single-clarification limit, cue-only presentation changes, one parser retry, evaluator separation, checkpoint/failure logging, and v2 tidy-row analysis.
- Test history: the first focused run had 2 assertion failures and 1 missing test import; corrected event expectations/import. The next expanded run had 1 failure because the test compared raw JSON text before decoding JSONL escaping; fixed the test to verify exact base64 response bytes. A later analysis/controller run exposed 4 `UnboundLocalError` errors for terminal-failure results; initialized the returned failure from the terminal event and reran successfully. These initial failures were preserved here; no experiment responses were fabricated or discarded.
- Final validation: `python -m compileall -q src tests` passed; focused Phase 2 plus analysis tests **19 passed, 0 failed**; final full `python -m unittest discover -s tests -v` **66 passed, 0 failed**. Three access/schema JSON files parse. `git diff --check` reported four intentional two-space Markdown hard-breaks in the frozen analysis-plan metadata; no code whitespace issue was reported. All provider/controller checks used scripted turns and fake HTTP transports. **Zero live provider probes and zero live model calls.**
- Rechecked process/user/machine environment variable presence after the pause without reading values: OpenAI, Anthropic, Google/Gemini API keys and AWS profile/credential variables remain absent. Initial inventory remains at `artifacts/phase2_model_access.json` (SHA-256 `0BFF6230F207E790E250536C3CB7ECBE316193608775403D22266CACDB6C57E5`); post-pause recheck is `artifacts/phase2_model_access_recheck.json` (SHA-256 `C1023DCB78F8B54044C6DB4D11B7F9AB84F12677E47A4FF4EB4FF4308E3B3CF7`). The frozen plan is `analysis/analysis_plan.md` (SHA-256 `19313BAB9808430735BAA67B0C8AEF3F26BF4C9A8D2D4A7CFD27C088DBEB65DD`); model-owned output schema v2 is `schemas/agent_output.v2.schema.json` (SHA-256 `15001674FC78FFE397CD34EF7CEC3E3CC38E198AE8380B8BBD5D62420B6EF49E`). Neither exact model IDs nor two-family access are established.
- Source review and credential-token scan were clean. Local implementation commit `a98f1b0` was created as authorized, but `git push origin main` failed with Windows SChannel `SEC_E_NO_CREDENTIALS`; the Phase 2 commit is local and not yet on GitHub. The pre-existing warning about the inaccessible user-level Git ignore file remains harmless.
- **Next action:** restore GitHub credentials and push the local Phase 2 commits; separately make two distinct, budget-approved provider families accessible through environment credentials (never commit keys), choose exact model IDs/settings, estimate live pilot cost/runtime, then run the small live access pilot. Do not start the 1,920-run core or freeze the full experiment until the live checkpoint/pilot criteria pass.

| 2026-09-30 | PHASE 2 — OFFLINE BUILD | Implement provider adapters, v2 model-output parser, ordered live controller, versioned trial hashing, and v2 analysis support | Initial tests exposed harness expectation/import errors and one controller terminal-failure return bug; all were recorded and corrected. Final focused suite 19/19 passed; full suite 66/66 passed; compileall passed. Fake transports only; no provider probes or live model calls. | `src/before_recommendation/{model_adapters,live_controller,live_output,analysis}.py`; `schemas/agent_output.v2.schema.json`; `tests/test_live_model_path.py`; `artifacts/phase2_model_access_recheck.json` | Obtain two provider families and exact model IDs, then estimate and run the live pilot; the core experiment remains gated. |
| 2026-09-30 | PHASE 2 — OFFLINE BUILD | Review, commit, and publish the validated offline build | Credential-token scan clean; local commit `a98f1b0` created. Push attempted as authorized but failed: Windows Git SChannel reported `SEC_E_NO_CREDENTIALS`; no remote change occurred. This roadmap status is committed in the follow-up documentation commit. | Local `main` Phase 2 commits; `roadmap.md` | Restore GitHub authentication and push the local commits; live model access remains a separate checkpoint. |

## Phase 2 access and synchronization recheck — 2026-09-30T17:14Z

**Status: STOPPED BEFORE LIVE RESEARCH at Checkpoint A. Main experiment NOT STARTED.**

- Re-read `project.md`, `roadmap.md`, `AGENTS.md`, and `analysis/analysis_plan.md` completely. Re-inspected the Phase 1 configuration, both output parsers, provider adapters, ordered live controller, and Phase 2 live-path tests. The repository contains no selected production `ModelConfig` or exact research model ID; constructor examples in tests are deterministic fakes only.
- Created and JSON-validated `artifacts/model_access_matrix.json` (SHA-256 `FCD4812DD3E2BFE621B8479AB2089892F0442AA604C7A16C479A244840EE90BF`). Environment-variable presence was checked in process, user, and machine scopes without printing or recording credential values. `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `GEMINI_API_KEY`, AWS credential/profile variables, and Azure OpenAI variables were absent. The Codex session exposes `gpt-6-luna` through ChatGPT-managed authentication, which is not an eligible research API adapter endpoint.
- The OpenAI and Anthropic adapters, strict/tool schema paths, and offline catalog protocol are implemented and fake-transport-tested. Neither provider is actually configured or accessible: both lack credentials and exact model IDs. Google Gemini has no repository adapter and no credential. Thus no two-family selection can be made. Matrix records adapter capability separately from live access and validation.
- Git state at inspection: clean `main`, HEAD `28ad158f0cf3d53a63fd6d6829b25a2fd3212a6d`, two local commits ahead of the last known `origin/main` tracking ref `015df787ca22fd3ce2cda9557e74b50b7884dc7d`. Fetch and normal push both failed with `schannel: AcquireCredentialsHandle failed: SEC_E_NO_CREDENTIALS (0x8009030E) - No credentials are available in the security package`; no remote HEAD was verified and no push succeeded. `gh` is installed, but `gh auth status` could not read `C:\Users\Bhagya\AppData\Roaming\GitHub CLI\config.yml` (`Access is denied`), so its authentication state could not be determined.
- **No live access probes or 32-run pilot were attempted.** Live calls remain zero; pilot completed runs zero; main planned runs 1,920, completed zero. The controller protocol implies 2–4 turns per valid run (3,840–7,680 total turns if all core runs complete without technical reruns); this is only a protocol bound, not an expected-call estimate. No model-specific price or observed usage is available, so cost/runtime estimates are unavailable. No experiment freeze or preflight artifact was created. Analysis, data quality, and robustness are not started.
- No implementation code changed in this recheck. The prior offline validation remains the recorded result: compileall passed and the full suite passed 66/66 using deterministic fakes.
- **Exact next action:** authenticate GitHub through the normal user-driven `gh auth login` flow (or restore access to the existing CLI config) so the local commits can be fetched/pushed normally; configure `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` locally without adding values to source; select one exact accessible model ID for each family and an approved budget ceiling. Then rerun the access gate.

| Date/time | Phase | Action | Result | Files/artifacts | Next action |
|---|---|---|---|---|---|
| 2026-09-30T17:14Z | PHASE 2 — ACCESS GATE | Recheck GitHub synchronization and provider access; create provider matrix | Git fetch/push both failed with Windows SChannel `SEC_E_NO_CREDENTIALS`; GitHub CLI status was unreadable due access denied to its config. No API credentials or exact model IDs for two families are configured. No live probes/calls or experiment runs. Matrix records adapter support separately from configured/live-validated access. | `artifacts/model_access_matrix.json`; local `main` HEAD at inspection `28ad158f0cf3d53a63fd6d6829b25a2fd3212a6d` | Restore GitHub CLI authentication, configure the two provider credentials and exact model IDs locally, and repeat the access gate. |
| 2026-09-30T17:18Z | PHASE 2 — GIT CHECKPOINT | Commit the access matrix/roadmap and retry normal push | Local commit `09aa233ef5a071b1a3c28c97b038f93de121049c` created. A normal push after the commit failed again with `SEC_E_NO_CREDENTIALS`; no remote update or remote HEAD verification. Working tree is clean; local `main` is three commits ahead of its last-known `origin/main` tracking ref. | `artifacts/model_access_matrix.json`; `roadmap.md`; commit `09aa233ef5a071b1a3c28c97b038f93de121049c` | User authenticates GitHub CLI (`gh auth login`) or restores its config access; then push normally and verify remote HEAD. |

## Phase 2 current provider-candidate gate — 2026-09-30T18:03Z

**Status: STOP at candidate access filtering. No live research started.**

- Re-read `project.md`, `roadmap.md`, `AGENTS.md`, and `analysis/analysis_plan.md` completely. The current user instruction sets OpenAI, Google Gemini, and Groq as candidates and explicitly excludes Anthropic/Claude from selection. No research assumptions or core design were changed.
- Checked only presence of `OPENAI_API_KEY`, `GEMINI_API_KEY`, and `GROQ_API_KEY` in process, user, and machine environment scopes. All three are absent. No exact model IDs or provider model configuration were found. Credential values were not printed or recorded.
- Updated `artifacts/model_access_matrix.json` to version 1.1.0 (SHA-256 `451956DCB63490FE8A03A0AE6C07172D45B3E0C57F8DBECEE4E2875BF21C8D76`). The OpenAI adapter exists but has no credential/model; Gemini and Groq credentials are absent and no adapters exist for either. Groq's underlying model family cannot be inferred without an exact model ID and provider metadata. There are zero configured candidate models and zero viable families; Anthropic is excluded from this candidate set.
- No model-list request, live access probe, price lookup, free-tier/quota check, rate-limit check, or 32-run pilot was made. Exact models and account access are unavailable, so the lowest-cost eligible pair and per-valid-run cost cannot be calculated without guessing. The 1,920-run core remains NOT STARTED; no freeze or selection artifact was created.
- Git state at inspection: working tree was clean; local `main` and its last-known `origin/main` tracking ref both pointed to `98c8ea4c34e74c211015b1ef0d3dc08060db0a94` (0 ahead/0 behind). A fresh `git fetch origin main` failed with `SEC_E_NO_CREDENTIALS (0x8009030E)`, so the actual remote HEAD was not independently verified. `gh auth status` remains unable to read the GitHub CLI config (`Access is denied`).
- Matrix JSON validation passed; no code changed, so the recorded offline test result remains 66/66 passed and compileall passed from the prior implementation milestone. No live model calls were made.
- **Exact next action:** configure at least two intended provider credentials locally (without sending or committing values), select exact models from their provider metadata, and then implement/test any missing Gemini/Groq adapter(s) before live probes. Restore GitHub CLI configuration access or authenticate so a fresh fetch can verify the remote.

| 2026-09-30T18:03Z | PHASE 2 — ACCESS GATE | Recheck current candidate provider access and update matrix per current instruction | Presence checks found no OpenAI, Gemini, or Groq keys in any checked scope. No exact model IDs, no Gemini/Groq adapters, zero viable families. No probes, pilot, pricing/quota checks, or empirical calls. JSON validation passed. Fresh Git fetch failed with `SEC_E_NO_CREDENTIALS`; local branch/tracking ref matched at inspection but remote was not freshly verified. | `artifacts/model_access_matrix.json` v1.1.0; `roadmap.md` | Configure at least two provider credentials and choose exact distinct model families; implement selected missing adapter(s), then rerun the access gate. |
| 2026-09-30T18:07Z | PHASE 2 — GIT CHECKPOINT | Commit refreshed candidate matrix and retry normal push | Local commit `cb57bec085f0de630650a5b3cad7b7d41298e370` created. Normal push failed with `SEC_E_NO_CREDENTIALS`; no remote update or fresh remote HEAD verification. At this check, local `main` was one commit ahead of last-known `origin/main` `98c8ea4c34e74c211015b1ef0d3dc08060db0a94`. | `artifacts/model_access_matrix.json`; `roadmap.md`; commit `cb57bec085f0de630650a5b3cad7b7d41298e370` | Restore GitHub CLI/Git credential access, then push normally and verify remote HEAD. |

## Phase 2 access recheck — 2026-09-30T18:39:36Z

**Status: STOP at the credential gate. No provider or model requests were made.**

- Re-read `project.md`, `roadmap.md`, `AGENTS.md`, and `analysis/analysis_plan.md` completely before this checkpoint. The instructed candidate set remains OpenAI, Google Gemini, and Groq; Anthropic/Claude remains excluded.
- Rechecked only presence of `OPENAI_API_KEY`, `GEMINI_API_KEY`, and `GROQ_API_KEY`. All three are **NOT SET** in the current Process, User, and Machine environment scopes. Values were neither printed nor recorded. This execution environment cannot see the newly reported persistent credentials, so the authorized next step cannot proceed to provider discovery or adapter implementation.
- A fresh `git fetch origin main` failed with `SEC_E_NO_CREDENTIALS (0x8009030E)`. `gh auth status` also remains unable to read the GitHub CLI config (`Access is denied`). Local branch is `main`, HEAD is `0e2b11a37b5c0069fd0a8156d403e14954ed62a8`, and the last-known `origin/main` tracking ref is `98c8ea4c34e74c211015b1ef0d3dc08060db0a94` (2 commits ahead, 0 behind by the stale tracking ref). The remote HEAD was not verified and no push was attempted.
- Updated `artifacts/model_access_matrix.json` to v1.2.0 with the current scope-by-scope presence result, local Git snapshot, and blockers (SHA-256 `926B1B144946C8E5CA45EE500342AE8524EEB1D8096CA09A7EB60C144153598E`). No exact model IDs are configured; there are zero viable candidate families. No pricing/quota requests, live probes, pilot, selection, freeze, preflight, or main-experiment runs occurred. Anthropic was not substituted.
- Matrix JSON parse and assertions that all 3 keys are false in all 3 scopes: **PASS**. `git diff --check`: **PASS**. These are the only applicable checks for this documentation-only access-gate update; no code or provider-adapter tests were run. Historical Phase 1 test results remain as recorded and were not rerun at this checkpoint.
- **Exact next action:** make the intended provider variables visible to this Codex execution environment (restart/refresh it if required), then rerun presence-only checks. Do not send key values in chat. Once at least two intended credentials are visible, resume model discovery, official cost/quota verification, and missing adapter implementation with fake-transport tests before any live calls. Separately restore Git credential/config access so fetch and normal push can be verified.

| 2026-09-30T18:39:36Z | PHASE 2 — ACCESS GATE RECHECK | Verify newly reported provider environment and GitHub auth | All three keys were NOT SET in Process/User/Machine scopes. Fresh fetch failed with `SEC_E_NO_CREDENTIALS`; `gh auth status` could not read CLI config due `Access is denied`. No provider calls, adapter changes, tests, pilot, or main experiment. Matrix JSON parse/presence assertions passed; `git diff --check` passed. | `artifacts/model_access_matrix.json` v1.2.0 (SHA-256 `926B1B144946C8E5CA45EE500342AE8524EEB1D8096CA09A7EB60C144153598E`); `roadmap.md` | Refresh environment so at least two intended keys are visible; restore Git auth; rerun the access gate. |

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
| 2026-09-30 21:07 IST | PHASE 2 — PREFLIGHT | Inspect provider access and freeze the pre-data analysis plan | Checkpoint A failed: no two research API model families are accessible; no live probe or external model call was made. Added a model-access snapshot and frozen analysis plan. No code or experiment data changed. Full Phase 1 suite rerun: **49 passed, 0 failed**; model-access JSON parsed successfully. | `artifacts/phase2_model_access.json` (SHA-256 `0BFF6230F207E790E250536C3CB7ECBE316193608775403D22266CACDB6C57E5`); `analysis/analysis_plan.md` v1.0.0 (SHA-256 `19313BAB9808430735BAA67B0C8AEF3F26BF4C9A8D2D4A7CFD27C088DBEB65DD`); current Git commit to be recorded after commit | Resolve two-provider access, then implement and test real adapters and the strictly ordered live trial controller. |

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
