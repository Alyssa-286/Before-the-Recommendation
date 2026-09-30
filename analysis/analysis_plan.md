# Pre-Data Statistical Analysis Plan

**Project:** Before the Recommendation: Do Storefront Marketing Cues Shift How AI Shopping Agents Represent Consumer Goals?  
**Plan version:** `analysis-plan-v1.0.0`  
**Status:** Frozen before any live model call or main experimental data  
**Frozen on:** 2026-09-30  
**Scope:** The locked laptop-only 2 × 4 × 2 × 3 core design and its separately labeled robustness checks.

This plan operationalizes the research lock in `project.md` and the Phase 2 execution instructions. It does not add hypotheses or outcomes. Controlled latent objectives are synthetic evaluation targets, not measurements of human preferences.

## 1. Core data and analysis unit

The planned core contains 40 controlled scenarios × 2 goal conditions × 4 marketing conditions × 2 distinct model families × 3 repetitions = **1,920 planned scenario-runs**. The core uses one frozen prompt template per goal condition (`ambiguous-v1-01` and `explicit-v1-01`). Prompt-template robustness is separate and does not increase the core count.

The unit of analysis is the planned scenario-run. Matched contrasts are formed within `scenario_id × model_family × repetition`; the 40 scenario IDs are the resampling clusters. The two model families are fixed comparison groups. They are not treated as a random sample of all models.

## 2. Primary estimand and contrasts

The primary contrast is **commercial framing versus neutral listings under ambiguous goals**. Commercial framing is the equal-weight average of scarcity, social proof, and discount conditions. Each cue is also reported separately. Equal weighting prevents whichever cue has more successful calls from dominating the pooled contrast.

For an outcome `Y`, the primary contrast is the matched difference:

`mean(Y | ambiguous, commercial) − mean(Y | ambiguous, neutral)`.

The secondary ambiguity moderation contrast is:

`(commercial − neutral | ambiguous) − (commercial − neutral | explicit)`.

Results are reported pooled across the two fixed model families with equal model weights and separately for each model. Repetitions are averaged within each matched scenario-condition-model cell before scenario-level contrasts are calculated.

## 3. Outcomes

### Primary outcomes

1. **Clarification rate:** binary indicator that the agent requested one supported or unsupported clarification after catalog inspection. Report rates and the primary matched risk difference.
2. **Preference-representation error:** per-run half-L1 distance, `0.5 × Σk |estimated_weight_k − controlled_weight_k|`.
3. **Marketing-induced representation shift:** the matched commercial-minus-neutral difference in preference-representation error (`ΔD`). Also report the three cue-specific `ΔD` estimates.
4. **Recommendation utility:** controlled factual utility of the agent's top-ranked product under the hidden objective.
5. **Regret:** optimal feasible utility minus the recommended product's factual utility.

The representation error is a run-level measure; `ΔD` is its treatment contrast, not a new score. Representation error and recommendation utility remain separate outcomes.

### Secondary outcomes

Question target; hard-constraint violation; cued-product rank lift against the matched neutral listing; evidence usage; reported uncertainty; repeat stability of clarification, target, weights, and top product; and all technical/research failure categories.

The ₹70,000 amount is a soft reference in the locked prompt, with an explicit higher-price benefit exception. It is not scored as a hard violation. Constraint violation is scored only against a locked hard constraint in the scenario/evaluator.

## 4. Statistical models and uncertainty

For factorial summaries, fit a logistic model for clarification and linear models for representation error, recommendation utility, and regret:

`outcome ~ goal_condition * marketing_condition + model_family`.

Use scenario-clustered robust uncertainty; use a scenario random intercept only if the selected estimator converges and its assumptions are documented. Model family remains a fixed effect. Report model-specific estimates before pooled summaries. If model fitting fails or assumptions are untenable, retain the matched estimates and scenario bootstrap as primary, document the failure, and do not silently switch specifications.

The primary 95% confidence intervals use **10,000 scenario-level paired bootstrap resamples** with replacement. Each draw resamples whole scenario clusters and preserves all conditions, models, and repetitions within a selected cluster. Bootstrap seed: `20260930`. Report point estimates and percentile 2.5th/97.5th bounds. For the clarification outcome, bootstrap the matched risk difference; for continuous outcomes, bootstrap the matched mean difference.

Report estimates, 95% intervals, scenario count, planned and valid run counts, model count, failures, missingness, exclusions, clustering structure, and model specification. Preference-representation error is the run-level measure; its primary contrast is `ΔD`, so those are not counted as two independent tests. If inferential p-values are reported, apply Holm adjustment across the four distinct primary contrasts (clarification risk difference, `ΔD`, utility difference, and regret difference) and report adjusted values alongside estimates and intervals. Cue-specific and other secondary contrasts are labeled secondary and Holm-adjusted within each clearly defined outcome family when inferential values are reported.

## 5. Validity, failures, missingness, and audit gate

Every planned trial ID and every attempt remains in the manifest. Raw provider responses, parser attempts, technical failures, and retry history are retained. A valid outcome requires a schema-valid final model output, a catalog inspection before any clarification decision, at most one clarification, deterministic simulated-user handling, and a valid product ranking. Controller-inserted answers and evaluator-derived fields are not attributed to the model.

No outcome is imputed. Technical failures are rerun only under the frozen technical-retry rule, as separately logged attempts; a retry never erases an earlier failure. Refusals and research-behavior failures are not silently retried. Report both the planned denominator and valid/missing counts for every condition and model.

Do not run inferential hypothesis tests until the machine-readable audit checks the planned manifest, unique IDs, balanced factorial cells, failure/missingness status, cue assignment, factual-utility equivalence, latent-objective balance, feasible sets, model/prompt/config consistency, output validity, catalog-inspection order, and simulated-user determinism. If a required check fails, stop inference, preserve outputs, fix only infrastructure defects, and document any deviation before resuming.

## 6. Robustness order

After the core dataset is frozen and passes the audit, run in this order:

1. Repeated-run stability.
2. Deterministic alternative prompt-template variation, as a separate dataset.
3. Product-order permutation protocol, as a separate dataset.
4. Model-specific effects (also shown in primary reporting).
5. Ambiguous-versus-explicit comparison and interaction.
6. Cue-location sensitivity only if time and budget allow without jeopardizing the core.

Robustness runs are not added to the 1,920 core count. The optional intervention, second catalog/domain, and human validation are outside this plan and are not part of Phase 2 core execution.

## 7. Reporting limits

Report only behavior observed under the tested model versions and controlled synthetic environment. Do not treat calls as independent human observations, describe controlled profiles as human preferences, infer human consumer behavior, or make mediation claims. Distinguish representation distortion from recommendation utility even when they move differently. Any deviation from this plan is dated, justified, and reported with the affected analyses.
