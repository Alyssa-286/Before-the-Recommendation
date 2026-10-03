## Abstract

AI shopping agents now stand between firms' product information and consumers' goals, so customer-centric evaluation must ask whether the agent represented the goal faithfully, not only whether its recommendation was good. In a pre-specified audit in a synthetic laptop storefront, 40 controlled objectives were crossed with ambiguous versus explicit goal statements and four storefront conditions (neutral, scarcity, social proof, discount). Gemini 3.1 Flash-Lite and Ministral 14B acted as tool-using agents under a fixed protocol: inspect the catalog, optionally ask one question to a deterministic simulated user, then submit preference weights and a ranking. Of {{n_planned}} runs, {{n_valid}} were valid. Goal ambiguity raised representation error D (ambiguous minus explicit: {{h1_representation_error}}). Under ambiguity, commercial cues left representation unchanged (ΔD = {{prim_representation_error}}), but lowered clarification ({{prim_clarification}}) and slightly lowered utility ({{prim_recommended_utility}}), mainly for one model. These two cue effects replicated when the labels were moved to a different product set but not under an alternate request wording or a permuted product order; the null representation shift replicated in all three checks. Almost all clarification questions were multi-attribute trade-offs that the simulated user could not answer. The study involves no human participants; it shows that goal representation and recommendation can respond differently to storefront framing and should be audited separately.

**Keywords:** AI shopping agents; agentic commerce; storefront marketing cues; preference elicitation; customer-centricity; recommendation audit; clarification

<!-- BODY -->

### 5.6 Measures and conditions at a glance

[[TABLE1]]

[[TABLE_METRICS]]

[[TABLE2]]

![Figure 1. Conceptual framework.](../outputs/figures/fig1_conceptual_framework.png)

![Figure 2. Experimental pipeline and evaluator isolation.](../outputs/figures/fig2_experimental_pipeline.png)

## 6. Results

### 6.1 Execution and data quality

All {{n_planned}} planned core runs were executed under the frozen configuration. Gemini 3.1 Flash-Lite ran through three free-tier projects and Ministral 14B through Mistral's free mode, using {{total_calls}} provider calls and {{total_tokens}} tokens at zero cost. {{n_valid}} runs were valid ({{valid_pct}}): {{google_gemini_valid}} for Gemini and {{mistral_valid}} for Ministral. The {{n_failed}} terminal failures, all Ministral ({{mistral_failed}}), are retained in every denominator; Gemini had {{google_gemini_failed}}. One corrected submission after a schema error (the parser retry) was used in {{google_gemini_parser_retries}} Gemini and {{mistral_parser_retries}} Ministral runs. The frozen technical re-run for provider failures was triggered {{google_gemini_tech_retries}} times for Gemini and {{mistral_tech_retries}} times for Ministral. Because the execution process was interrupted and resumed, {{google_gemini_requeued}} Gemini and {{mistral_requeued}} Ministral trials that were in flight were re-run from their first turn. Their partial earlier attempts are preserved.

The data-quality audit ({{audit_checks}} checks) {{audit_passed}}. Its checks cover coverage, unique identifiers, frozen hashes, identical catalog facts and correct cue placement across arms, inspection-before-clarification order, simulated-user determinism, and independent recomputation of all metrics from raw outputs. An automated scan of all {{requests_scanned}} model-visible requests found no latent-objective, optimum, utility or arm-name leakage.

### 6.2 Clarification behaviour

Figure 3 shows clarification rates by cell. Under ambiguous goals Gemini asked a clarification question in {{clar_google_gemini_ambiguous_neutral}} of neutral-arm runs and in {{clar_google_gemini_ambiguous_scarcity}}, {{clar_google_gemini_ambiguous_social_proof}} and {{clar_google_gemini_ambiguous_discount}} of the scarcity, social-proof and discount runs. Ministral asked in {{clar_mistral_ambiguous_neutral}} of neutral runs but in {{clar_mistral_ambiguous_scarcity}} of scarcity runs and {{clar_mistral_ambiguous_social_proof}} of social-proof runs.

The primary commercial-minus-neutral risk difference under ambiguity was {{prim_clarification}}; {{prim_clarification_verdict}} (Holm-adjusted p {{prim_clarification_holm}}). By model it was {{prim_clarification_google_gemini}} for Gemini and {{prim_clarification_mistral}} for Ministral. By cue it was {{cue_scarcity_clarification}} for scarcity, {{cue_social_proof_clarification}} for social proof and {{cue_discount_clarification}} for discount framing. Under explicit goals the commercial-minus-neutral difference was {{exp_clarification}}. The ambiguous-minus-explicit difference in clarification, averaged over arms, was {{h1_clarification}}.

What the agents asked matters as much as whether they asked. Only single-dimension questions receive an informative answer from the simulated user: {{supported_google_gemini}} of Gemini's {{nclar_google_gemini}} clarifications and {{supported_mistral}} of Ministral's {{nclar_mistral}}. Almost every question asked the shopper to compare two or more attributes ("which is more important: price or durability?") or asked about an attribute outside the objective, such as battery life. Under the frozen answer function both kinds receive the standard uncertainty answer. Pairwise questions are reasonable in themselves; the low informative-answer rate is therefore a joint property of the agents' questioning style and the simulated user's frozen single-dimension design. Normalized question targets under ambiguity were: Gemini, {{qt_google_gemini}}; Ministral, {{qt_mistral}}.

![Figure 3. Clarification rate by goal, storefront condition and model.](../outputs/figures/fig3_clarification.png)

### 6.3 Preference-representation error (H1–H3)

Figure 4 shows representation error D by cell. With neutral listings, mean D was {{D_google_gemini_ambiguous_neutral}} (Gemini) and {{D_mistral_ambiguous_neutral}} (Ministral) under ambiguous goals, against {{D_google_gemini_explicit_neutral}} and {{D_mistral_explicit_neutral}} under explicit goals. Averaged over storefront conditions, the ambiguous-minus-explicit difference in D was {{h1_representation_error}}; {{h1_representation_error_verdict}}. By model it was {{h1_representation_error_google_gemini}} for Gemini and {{h1_representation_error_mistral}} for Ministral. **H1 is {{H1_verdict}}.**

The primary marketing-induced shift under ambiguity was ΔD = {{prim_representation_error}}; {{prim_representation_error_verdict}} (Holm-adjusted p {{prim_representation_error_holm}}). By model, ΔD was {{prim_representation_error_google_gemini}} for Gemini and {{prim_representation_error_mistral}} for Ministral. By cue it was {{cue_scarcity_representation_error}} for scarcity, {{cue_social_proof_representation_error}} for social proof and {{cue_discount_representation_error}} for discount framing. **H2 is {{H2_verdict}}.** Under explicit goals the commercial-minus-neutral ΔD was {{exp_representation_error}}, and the moderation contrast (ambiguous minus explicit) was {{mod_representation_error}}. **H3 is {{H3_verdict}}.** The null ΔD is informative because the interval is narrow. Its largest bound in absolute value is {{dD_bound_share}} of the ambiguity effect on D.

![Figure 4. Preference-representation error D by goal, storefront condition and model.](../outputs/figures/fig4_representation_error.png)

### 6.4 Recommendation utility and regret (H4)

Figure 5 shows utility and regret. Under ambiguity the primary commercial-minus-neutral contrasts were {{prim_recommended_utility}} for utility ({{prim_recommended_utility_verdict}}; Holm-adjusted p {{prim_recommended_utility_holm}}) and {{prim_regret}} for regret. By model, the utility contrast was {{prim_recommended_utility_google_gemini}} for Gemini and {{prim_recommended_utility_mistral}} for Ministral. By cue it was {{cue_scarcity_recommended_utility}} for scarcity, {{cue_social_proof_recommended_utility}} for social proof and {{cue_discount_recommended_utility}} for discount framing. Under explicit goals the contrast was {{exp_recommended_utility}} pooled: {{exp_recommended_utility_google_gemini}} for Gemini and {{exp_recommended_utility_mistral}} for Ministral. These utility effects are small in absolute terms; the regret scale is shown in Figure 5.

Each ambiguous-goal commercial run was matched to the neutral run of the same scenario, model and repetition, giving {{h4_pooled_ambiguous_pairs}} pairs. The top product changed in {{h4_pooled_ambiguous_topchg}} of pairs: {{h4_google_gemini_ambiguous_topchg}} for Gemini and {{h4_mistral_ambiguous_topchg}} for Ministral. The represented weights moved by more than 0.05 in {{h4_pooled_ambiguous_shifted}} of pairs, and in {{h4_pooled_ambiguous_shift_same_top}} of pairs they moved while the top product stayed the same. These weight movements were not systematically toward or away from the controlled objective, which is why ΔD is close to zero. **H4: {{H4_verdict}}.** Figure 6 plots each matched pair's ΔD against its utility change.

[[TABLE3]]

[[TABLE_MODEL]]

![Figure 5. Recommendation utility and regret by condition and model.](../outputs/figures/fig5_utility_regret.png)

![Figure 6. Representation shift versus utility change in matched pairs (ambiguous goal).](../outputs/figures/fig8_representation_vs_utility.png)

### 6.5 Secondary and exploratory outcomes

Under ambiguity, commercial cues changed the share of runs whose top product was one of the five cued products by {{sec_ambiguous_top_is_cued}}. This was {{sec_ambiguous_top_is_cued_google_gemini}} for Gemini and {{sec_ambiguous_top_is_cued_mistral}} for Ministral, so the Ministral utility loss coincides with a shift toward cued products. The mean rank of the cued products changed by {{sec_ambiguous_cued_mean_rank}} positions (negative means ranked higher).

Cue language entered the agents' stated evidence or explanations: the share of runs citing it rose by {{sec_ambiguous_evidence_mentions_cue}}. Under the discount arm with an ambiguous goal, {{cueev_google_gemini_ambiguous_discount}} of Gemini runs and {{cueev_mistral_ambiguous_discount}} of Ministral runs cited the promotion. Reported uncertainty changed by {{sec_ambiguous_uncertainty}}.

No locked hard constraint applies in this environment (the ₹70,000 amount is a soft reference), and the constraint-violation contrast is {{sec_ambiguous_constraint_violated}}. For the exploratory H5, the discount-minus-neutral difference in price-related clarification was {{h5_pooled}} under ambiguous goals (Gemini {{h5_google_gemini}}; Ministral {{h5_mistral}}) and {{h5_explicit}} under explicit goals; H5 is {{H5_verdict}}.

## 7. Robustness

The checks are reported in the frozen order.

- **(1) Repeat stability.** Across the three repetitions of a cell, Gemini agreed on the clarification decision in {{stab_google_gemini_clar}} of cells and on the top product in {{stab_google_gemini_top}}, with a mean maximum pairwise weight spread of {{stab_google_gemini_spread}}. For Ministral the corresponding figures were {{stab_mistral_clar}}, {{stab_mistral_top}} and {{stab_mistral_spread}}. Run-to-run variability is therefore of the same order as the cue-induced weight shifts reported above.
- **(2) Alternate request template** ({{robust_template_status}}): ΔD = {{robust_template_representation_error}}; clarification difference {{robust_template_clarification}}; utility difference {{robust_template_recommended_utility}}.
- **(3) Permuted product order** ({{robust_order_status}}): ΔD = {{robust_order_representation_error}}; clarification difference {{robust_order_clarification}}; utility difference {{robust_order_recommended_utility}}.
- **(4–5) Model-specific effects** and **the ambiguous-versus-explicit comparison** are reported in Section 6.
- **(6) Relocated cue set**, where labels were placed on a different, independently drawn set of five products ({{robust_cue_location_status}}): ΔD = {{robust_cue_location_representation_error}}; clarification difference {{robust_cue_location_clarification}}; utility difference {{robust_cue_location_recommended_utility}}.

Checks (2), (3) and (6) are separate datasets (ambiguous goal, 40 scenarios, all four storefront conditions, both models, one repetition) and are never pooled with the core.

The factorial models (outcome ~ goal × marketing + model, scenario-clustered SEs) are archived with full coefficients. Fit details are: clarification, {{fm_clarification_note}}; D, {{fm_representation_error_note}}; utility, {{fm_recommended_utility_note}}; regret, {{fm_regret_note}}.

[[TABLE4]]

![Figure 7. Primary contrasts by model and robustness dataset (95% scenario-bootstrap intervals).](../outputs/figures/fig6_cross_model_robustness.png)

## 8. Failure Analysis

Two kinds of failure are separated in the archived data.

- **Infrastructure events** produced no model output: provider 5xx errors and per-minute or daily quota responses. They are absorbed at the transport level and logged per request, and never alter a trial.
- **Terminal trial failures** are model-behaviour or protocol outcomes. Gemini had {{google_gemini_failed}}. Ministral's were {{fail_detail_mistral}}. Most were plain-text answers without the required tool call. None was a provider failure, so none was eligible for the frozen technical re-run.

Table 5 applies the pre-specified behavioural taxonomy to all planned runs.

- **Questioning:** under-questioning (no question despite ambiguity) {{tax_under_questioning}} runs ({{tax_under_questioning_google_gemini}} Gemini, {{tax_under_questioning_mistral}} Ministral); over-questioning (a question despite an explicit goal) {{tax_over_questioning}}; silent defaulting (no question, uncertainty ≤ 0.20) {{tax_silent_defaulting}}.
- **Cue use:** unsupported marketing evidence {{tax_unsupported_marketing_evidence}}; leading clarification {{tax_leading_clarification}}; cue-driven attribute substitution {{tax_cue_driven_attribute_substitution}}.
- **Internal consistency:** ranking inconsistency with the agent's own weights {{tax_ranking_inconsistency}}; uncertainty failure (D ≥ 0.25, uncertainty ≤ 0.20) {{tax_uncertainty_failure}}; preference-weight instability across repetitions {{tax_preference_weight_instability}}.

The cue-term detector is a fixed keyword list with a non-zero neutral baseline, so commercial-minus-neutral differences are the meaningful quantities. Figure 8 traces one case selected by a rule fixed in code: the most frequent behavioural category among ambiguous commercial runs, then the first trial by identifier.

[[TABLE5]]

![Figure 8. Representative failure pathway (selected by a pre-specified rule).](../outputs/figures/fig7_failure_pathway.png)

## 9. Discussion

**What the data show.** Under the controlled environment, the explicitness of the goal statement mattered far more for representation fidelity than storefront framing did. Making priorities explicit reduced representation error substantially and consistently in both model families (H1). Ordinary scarcity, social-proof and discount labels left the represented goal essentially unchanged on average (H2 and H3 not supported). The cues nonetheless changed behaviour around the representation. They reduced how often one agent paused to ask for clarification, especially under scarcity framing. They also shifted that agent's final choices toward cued products, with a small but consistent loss of utility. The resulting dissociation is the reverse of H4's expectation: the recommendation moved while the represented goal did not. The robustness datasets qualify this picture. The null representation shift replicated under an alternate request wording, a permuted product order and a relocated cue set. The cue effects on clarification and utility replicated when the labels were moved to a different, independently drawn set of products. Ministral's share of cued top products rose by {{robust_cue_location_top_is_cued_mistral}}, so its choices follow whichever products carry a cue. These effects did not replicate under other presentations. With the alternate wording the clarification effect reversed sign ({{robust_template_clarification}}), and with permuted order both effects were indistinguishable from zero. They are therefore genuine for Ministral in the core presentation, but contingent on request wording and listing order.

**What the results may mean.** For marketing, this pattern is a caution against evaluating AI intermediaries through any single lens. Auditing representation alone would have judged framing harmless; auditing final picks alone would have missed that framing also suppressed clarification for one agent. Customer-centric evaluation needs both views plus the process view.

The clarification results add a second lesson. Both agents typically asked pairwise or multi-attribute trade-off questions. Gemini asked, for example, "which is more important to you: keeping the price as low as possible, or prioritizing higher durability for long-term use throughout college?" Ministral often asked about battery life, which is not part of the controlled objective. Under the frozen protocol, the simulated shopper answers only single-dimension questions, so it could not use these. Asking was common but informative asking rare; question frequency is not a measure of customer-centricity.

Finally, Gemini asked under every ambiguous request regardless of storefront, while Ministral's asking and choices responded to cues: conclusions must be model-specific.

**What the study cannot establish.** Effects on human shoppers, generality beyond two model versions and this catalog, and the question-to-representation pathway, which the frozen simulated user rarely exercised (Section 12).

## 10. Marketing and Customer-Centric Implications

First, customer-centric metrics for AI intermediaries should combine three things:
- *goal-representation fidelity*, measured here as D against a known objective and measurable in practice with test personas, much as mystery shopping audits human sales staff
- *recommendation quality*
- *elicitation quality*, meaning whether questions are asked and whether they can be answered

These moved independently in this study.

Second, storefront framing can act on agent behaviour, in some conditions, without distorting the stated goal representation. Firms and platforms should not treat an unchanged preference profile as evidence that their listing cues are neutral for agent-mediated customers.

Third, because the model families differed, firms deploying agents, and platforms hosting them, should audit the specific model and version they use. Vendor- or category-level assurances are not enough.

Fourth, the study offers a low-cost, reproducible audit template that marketing analytics teams can run before deployment: controlled personas, frozen storefront variants and a deterministic scorer. It was executed entirely within free API capacity.

## 11. Theoretical Implications

The results connect constructed-preference theory (Bettman et al., 1998) with agentic commerce by separating three stages that are often conflated: *elicitation* (whether and what to ask), *representation* (ŵ) and *selection* (the ranking). In this audit, ambiguity acted strongly on representation as well as on clarification frequency. Storefront cues never acted on representation; their effects on elicitation and selection appeared for one model and depended on wording and context. This is consistent with a view in which marketing context steers agent behaviour through process and choice rather than through a rewritten model of the customer. It also refines the argument that agents should help users construct preferences (Saracay et al., 2026): broad trade-off questions do not help a user who cannot yet state a trade-off.

Unlike instruction-driven commercial influence (Li, 2026; Wadi & Ma, 2026b), no instruction here favoured any product, yet one agent drifted toward cued listings, consistent with the storefront-architecture account of Wadi and Ma (2026a).

## 12. Limitations

**Environment and objectives.** The environment is synthetic. The laptops, scores and labels are templated, and the controlled objectives are evaluation targets, not measured human preferences. The simulated user answers only single-dimension questions and returns uncertainty otherwise. The agents mostly asked pairwise trade-off questions, so clarification was seldom informative. The question-to-representation pathway is therefore weakly tested, and the clarification results describe the frozen protocol, not what an answerable dialogue would produce.

**Models.** Only two model families were tested, each at one version with provider-default sampling. Repeated calls are not independent people, and model families are fixed comparison groups, not a sample of all AI systems.

**Cue manipulation and measurement.** Each commercial condition uses one wording and, in the core, one fixed set of five cued products; the relocation check varies the set but not the wording. The cue-term detector for evidence use is a keyword rule and has a non-zero neutral baseline. Effects on utility are small in absolute terms, and the regret scale depends on the catalog.

**Execution.** Free-tier quotas spread Gemini runs over several days.

**Pre-data deviations** (all documented before any core data): catalog regeneration under pre-specified acceptance criteria, a Gemini + Mistral pair under the zero-budget constraint, and ambiguous-goal-only robustness datasets. Ecological validity is therefore limited. Field data, human validation and additional categories are required before generalizing.

## 13. Research Integrity and Reproducibility

The hypotheses, the analysis plan (v1.0.0), the catalog acceptance criteria and the full execution configuration were committed before the corresponding data existed. The experiment freeze (`artifacts/experiment_freeze.json`) records file and configuration hashes.

Every raw provider response is preserved, along with every failed or interrupted attempt and every quota event. For each request the credential *variable name* is logged, never its value. The audit recomputes metrics independently from raw outputs. The analysis, figures, tables and every number in this manuscript are regenerated by scripts from the saved data, and the manuscript itself is rendered from computed results.

The code, configuration, data and audit reports are available in the project repository (https://github.com/Alyssa-286/Before-the-Recommendation). Execution used only free API capacity.

## 14. Conclusion

Before an AI shopping agent recommends anything, it forms a picture of what the customer wants. This audit measured that picture against a known objective. In the tested environment, an explicit goal statement improved the agent's representation far more than any storefront cue changed it. Ordinary marketing labels left the represented goal unchanged in every check. In the core design they changed whether one agent asked for clarification and which product it chose, an effect that followed the cue to whichever products carried it but depended on request wording and listing order. For marketers building or relying on AI intermediaries, customer-centricity therefore means auditing three things: the questions an agent asks, the goal it represents and the recommendation it makes.
