## Abstract

AI shopping agents increasingly stand between firms' product information and consumers' goals. Customer-centric evaluation should therefore ask both whether a recommendation is good and whether the agent represented the consumer's goal faithfully. We report a pre-registered-style controlled audit (frozen hypotheses and analysis plan) in a synthetic laptop storefront. Forty controlled latent objectives were crossed with ambiguous versus explicit goal statements and four storefront conditions (neutral, scarcity, social proof, discount framing). Two model families acted as tool-using agents: Gemini 3.1 Flash-Lite and Ministral 14B. A fixed protocol required catalog inspection before an optional single clarification, answered by a deterministic simulated user, followed by structured preference weights and a ranking. A deterministic evaluator measured representation error D (half-L1 distance to the controlled objective), utility and regret. Of {{n_planned}} planned runs, {{n_valid}} were valid ({{valid_pct}}); all failures are retained. Under ambiguous goals, the commercial-minus-neutral difference in representation error was {{prim_representation_error}}; for clarification it was {{prim_clarification}}, for utility {{prim_recommended_utility}} and for regret {{prim_regret}} (scenario-cluster bootstrap, 10,000 draws). Ambiguous goals versus explicit goals changed D by {{h1_representation_error}}. The findings describe two model versions in a synthetic environment with simulated users. They do not measure human consumer behaviour, but they show how representation fidelity can be audited separately from recommendation quality.

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

All {{n_planned}} planned core runs were executed under the frozen configuration: Gemini 3.1 Flash-Lite through two free-tier projects and Ministral 14B through Mistral's free mode. That required {{total_calls}} provider calls and {{total_tokens}} tokens, at zero cost. {{n_valid}} runs were valid ({{valid_pct}}): {{google_gemini_valid}} for Gemini and {{mistral_valid}} for Ministral. {{n_failed}} runs ended in terminal failures that are retained in all denominators: {{google_gemini_failed}} for Gemini and {{mistral_failed}} for Ministral. Parser retries occurred in {{google_gemini_parser_retries}} Gemini and {{mistral_parser_retries}} Ministral runs; technical re-runs in {{google_gemini_tech_retries}} and {{mistral_tech_retries}}. The data-quality audit ({{audit_checks}} checks) {{audit_passed}}. Its checks cover factorial coverage, unique trial identifiers, frozen templates and configuration hashes, byte-identical catalog facts across arms, cue placement, catalog-before-clarification ordering, simulated-user determinism, separation of raw and evaluator-only data, and independent recomputation of D, utility and regret from raw outputs. An automated scan of all {{requests_scanned}} model-visible requests found no latent-objective, optimum, utility or arm-name leakage.

### 6.2 Clarification behaviour

Figure 3 shows clarification rates by cell. Under ambiguous goals with neutral listings, Gemini asked a clarification question in {{clar_google_gemini_ambiguous_neutral}} of runs and Ministral in {{clar_mistral_ambiguous_neutral}}. Under explicit goals with neutral listings the rates were {{clar_google_gemini_explicit_neutral}} and {{clar_mistral_explicit_neutral}}. The primary commercial-minus-neutral risk difference under ambiguity was {{prim_clarification}}; {{prim_clarification_verdict}} (Holm-adjusted p = {{prim_clarification_holm}}). Model-specific estimates were {{prim_clarification_google_gemini}} for Gemini and {{prim_clarification_mistral}} for Ministral. Among ambiguous-goal clarifications, normalized question targets were: Gemini — {{qt_google_gemini}}; Ministral — {{qt_mistral}}. "Unsupported or compound" denotes questions that bundled several attributes or targeted a product; under the frozen protocol these receive the standard uncertainty answer.

![Figure 3. Clarification rate by goal, storefront condition and model.](../outputs/figures/fig3_clarification.png)

### 6.3 Preference-representation error (H1–H3)

Figure 4 shows representation error D by cell. With neutral listings and ambiguous goals, mean D was {{D_google_gemini_ambiguous_neutral}} for Gemini and {{D_mistral_ambiguous_neutral}} for Ministral. With explicit goals it was {{D_google_gemini_explicit_neutral}} and {{D_mistral_explicit_neutral}}. Averaged over storefront conditions, the ambiguous-minus-explicit difference in D was {{h1_representation_error}}; {{h1_representation_error_verdict}}. By model it was {{h1_representation_error_google_gemini}} for Gemini and {{h1_representation_error_mistral}} for Ministral. **H1 is {{H1_verdict}}.**

The primary marketing-induced shift under ambiguity was ΔD = {{prim_representation_error}}; {{prim_representation_error_verdict}} (Holm-adjusted p = {{prim_representation_error_holm}}). By model, ΔD was {{prim_representation_error_google_gemini}} for Gemini and {{prim_representation_error_mistral}} for Ministral. The cue-specific estimates were {{cue_scarcity_representation_error}} for scarcity, {{cue_social_proof_representation_error}} for social proof and {{cue_discount_representation_error}} for discount framing. **H2 is {{H2_verdict}}.** Under explicit goals the commercial-minus-neutral ΔD was {{exp_representation_error}}. The moderation contrast (ambiguous minus explicit) was {{mod_representation_error}}. **H3 is {{H3_verdict}}.**

![Figure 4. Preference-representation error D by goal, storefront condition and model.](../outputs/figures/fig4_representation_error.png)

### 6.4 Recommendation utility and regret (H4)

Figure 5 shows utility and regret. The primary commercial-minus-neutral contrasts under ambiguity were {{prim_recommended_utility}} for utility ({{prim_recommended_utility_verdict}}) and {{prim_regret}} for regret ({{prim_regret_verdict}}). In matched ambiguous-goal pairs, each commercial run compared with the neutral run of the same scenario, model and repetition, the top product changed in {{h4_pooled_ambiguous_topchg}} of {{h4_pooled_ambiguous_pairs}} pairs. The mean weight shift (half-L1 between ŵ in the two runs) was {{h4_pooled_ambiguous_shift}}. In {{h4_pooled_ambiguous_shift_same_top}} of pairs the weights moved by more than 0.05 while the top product stayed the same. **H4: {{H4_verdict}}.** Figure 8 plots each matched pair's ΔD against its utility change.

[[TABLE3]]

[[TABLE_MODEL]]

![Figure 5. Recommendation utility and regret by condition and model.](../outputs/figures/fig5_utility_regret.png)

![Figure 8. Representation shift versus utility change in matched pairs (ambiguous goal).](../outputs/figures/fig8_representation_vs_utility.png)

### 6.5 Secondary and exploratory outcomes

Commercial cues changed the mean rank of the cued products by {{sec_ambiguous_cued_mean_rank}} rank positions under ambiguity (a negative value means cued products were ranked higher). The share of runs whose top product was a cued product changed by {{sec_ambiguous_top_is_cued}}. Mentions of cue language in the agent's evidence or explanation changed by {{sec_ambiguous_evidence_mentions_cue}}; for example, under the discount arm with an ambiguous goal, {{cueev_google_gemini_ambiguous_discount}} (Gemini) and {{cueev_mistral_ambiguous_discount}} (Ministral) of runs cited cue language. Reported uncertainty changed by {{sec_ambiguous_uncertainty}}. No locked hard constraint applies in this environment; the ₹70,000 amount is a soft reference, so constraint violations are reported as {{sec_ambiguous_constraint_violated}}. For the exploratory H5, the discount-minus-neutral difference in price-targeted clarification was {{h5_pooled}} (Gemini {{h5_google_gemini}}; Ministral {{h5_mistral}}); H5 is {{H5_verdict}}.

## 7. Robustness

The robustness checks follow the frozen order. (1) *Repeat stability.* Across the three repetitions of a cell, Gemini agreed on the clarification decision in {{stab_google_gemini_clar}} of cells and on the top product in {{stab_google_gemini_top}}, with a mean maximum pairwise weight spread of {{stab_google_gemini_spread}}. For Ministral the figures were {{stab_mistral_clar}}, {{stab_mistral_top}} and {{stab_mistral_spread}}.

(2)–(3) and (6) are separate datasets: ambiguous goal, 40 scenarios, all four storefront conditions, both models, one repetition each. They are never pooled with the core.
- *Alternate request template* ({{robust_template_status}}): ΔD = {{robust_template_representation_error}}; clarification difference {{robust_template_clarification}}.
- *Permuted product order* ({{robust_order_status}}): ΔD = {{robust_order_representation_error}}; clarification difference {{robust_order_clarification}}.
- *Relocated cue set*, where labels were placed on a different, independently drawn set of five products ({{robust_cue_location_status}}): ΔD = {{robust_cue_location_representation_error}}; utility difference {{robust_cue_location_recommended_utility}}.

(4) Model-specific effects are reported throughout. (5) The ambiguous-versus-explicit comparison appears in Section 6.3. Factorial models (outcome ~ goal × marketing + model, scenario-clustered SEs) are archived with full coefficients: clarification {{fm_clarification_note}}; D {{fm_representation_error_note}}; utility {{fm_recommended_utility_note}}; regret {{fm_regret_note}}.

[[TABLE4]]

![Figure 6. Primary contrasts by model and robustness dataset (95% scenario-bootstrap intervals).](../outputs/figures/fig6_cross_model_robustness.png)

## 8. Failure Analysis

Failures fall into two kinds, which are separated in the archived data. Infrastructure events produce no model output: provider 5xx errors and per-minute or daily quota responses. These are absorbed at the transport level and logged per request. Terminal trial failures are model-behaviour or protocol outcomes. For Gemini these were {{fail_detail_google_gemini}}; for Ministral, {{fail_detail_mistral}}. Most Ministral failures were plain-text answers without the required tool call. None was eligible for the frozen technical re-run, which covers provider failures only, so all remain terminal.

Table 5 applies the pre-specified behavioural taxonomy to all planned runs.
- Questioning: under-questioning (an ambiguous goal with no question) occurred in {{tax_under_questioning}} runs ({{tax_under_questioning_google_gemini}} Gemini, {{tax_under_questioning_mistral}} Ministral), and over-questioning (a question despite an explicit goal) in {{tax_over_questioning}}. Silent defaulting, meaning no question under ambiguity with reported uncertainty ≤ 0.20, occurred in {{tax_silent_defaulting}}.
- Cue influence: unsupported marketing evidence, meaning cue language cited as evidence, occurred in {{tax_unsupported_marketing_evidence}}. Leading clarification occurred in {{tax_leading_clarification}}, and cue-driven attribute substitution, a cued top product that replaced the matched neutral choice, in {{tax_cue_driven_attribute_substitution}}.
- Internal consistency: ranking inconsistency relative to the agent's own stated weights occurred in {{tax_ranking_inconsistency}}, uncertainty failure (D ≥ 0.25 with uncertainty ≤ 0.20) in {{tax_uncertainty_failure}}, and preference-weight instability across repetitions in {{tax_preference_weight_instability}}.

Figure 7 traces one representative case chosen by a rule fixed in code: the most frequent behavioural category among ambiguous commercial runs, then the first trial by identifier.

[[TABLE5]]

![Figure 7. Representative failure pathway (selected by a pre-specified rule).](../outputs/figures/fig7_failure_pathway.png)

## 9. Discussion

[[VERIFY]] **What the data show.** In this controlled environment, the decisive factor for representation fidelity was whether the goal was stated (H1: {{H1_verdict}}). The storefront manipulation's effect on the represented goal was smaller and is summarised by the primary ΔD of {{prim_representation_error}} (H2: {{H2_verdict}}). The two model families differed in how often they asked for clarification and in what they asked about. That is a reminder that "the agent" is not a single behavioural type, and that audits must report results per model.

**What the results may mean.** For marketing, representation and recommendation are separable objects (H4: {{H4_verdict}}). An agent can reach the same top product while holding a different picture of what the customer values, or a different product while representing the goal equally well. A firm that evaluates its AI intermediary only on conversion or final-pick quality would miss representation drift. That drift matters when represented preferences are reused, for example for follow-up recommendations, personalization or bundle offers. Clarification behaviour is the lever here. A single well-targeted question about a supported dimension gives the agent information the storefront cannot. Compound or product-targeted questions waste it, because the simulated user cannot answer them and returns only uncertainty.

**What the study cannot establish.** The study observes two model versions, one synthetic catalog, simulated users with controlled objectives, and one cue placement scheme per condition. It does not show that human shoppers would be affected, that effects generalize to other agents, prompts or categories, or that any provider's deployed shopping product behaves this way.

## 10. Marketing and Customer-Centric Implications

First, customer-centric metrics for AI intermediaries should include *goal-representation fidelity*. Measured here as D against a known objective, it can be measured in practice with test personas, much as mystery shopping audits human sales staff. Second, ambiguity is where marketing context has room to act, so clarification design is a customer-centric investment. Agents should be encouraged to ask single, answerable questions about trade-offs and to treat storefront labels as claims, not evidence of the customer's preferences. [[VERIFY]] Third, because model families differed, firms deploying agents, and platforms hosting them, should audit the specific model and version they use. Vendor- or category-level assurances are not enough. Fourth, the study offers a low-cost, reproducible audit template that marketing analytics teams can run before deployment: controlled personas, frozen storefront variants, and a deterministic scorer.

## 11. Theoretical Implications

The results connect constructed-preference theory (Bettman et al., 1998) with agentic commerce. When a goal is underspecified, the agent's representation is constructed during inspection of a particular storefront. The framework separates *elicitation* (whether and what to ask), *representation* (ŵ) and *selection* (the ranking), and shows these stages can be measured separately. [[VERIFY]] That separation refines the recent argument that agents should help users construct preferences (Saracay et al., 2026). It also distinguishes the present cue-in-context channel from instruction-driven commercial influence (Li, 2026; Wadi & Ma, 2026b).

## 12. Limitations

The environment is synthetic. The laptops, scores and labels are templated, and the controlled objectives are evaluation targets, not measured human preferences. The simulated user answers only single-dimension questions and returns uncertainty otherwise, which shapes the value of asking. Only two model families were tested, each at one version with provider-default sampling. Repeated calls are not independent people, and model families are fixed comparison groups, not a sample of all AI systems. Each commercial condition uses one wording and one fixed set of five cued products in the core; the relocation check varies the set but not the wording. Execution depended on free-tier capacity, so Gemini runs were spread over several daily quota windows. The pre-data deviations were catalog regeneration under pre-specified criteria, replacement of the originally planned pair by Gemini + Mistral under the zero-budget constraint, and robustness datasets restricted to the ambiguous goal. All were documented before any core data existed. Ecological validity is therefore limited; field data, human validation and additional categories are required before generalizing.

## 13. Research Integrity and Reproducibility

Hypotheses, the analysis plan (v1.0.0), the catalog acceptance criteria and the full execution configuration were committed before the corresponding data existed. The experiment freeze (`artifacts/experiment_freeze.json`) records file and configuration hashes. Every raw provider response, every failed attempt, retry and quota event, and each request's credential *variable name* (never its value) are preserved. Metrics are recomputed independently from raw outputs in the audit. The analysis, figures, tables and every number in this manuscript are regenerated by scripts from the saved data; the manuscript is rendered from computed results. The code, configuration, data and audit reports are available in the project repository (https://github.com/Alyssa-286/Before-the-Recommendation). Execution used only free API capacity.

## 14. Conclusion

Before an AI shopping agent recommends anything, it decides what the customer wants. This audit shows that this decision can be measured against a known objective. [[VERIFY]] In the tested environment, the goal statement mattered more than storefront framing for representation fidelity. Representation and recommendation quality could diverge, and two model families behaved differently. For marketers building or relying on AI intermediaries, customer-centricity therefore means auditing not only the recommendation but the representation that precedes it.
