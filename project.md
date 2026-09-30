# Project Specification: Before the Recommendation

## Project Status

**Status:** Research locked; Phase 1 — Build

**Deadline:** 6 October 2026, hard deadline

**Researcher:** Solo technically strong undergraduate researcher

**Conference:** GBS 3rd National Conference on Marketing (attached conference PDF is authoritative for submission requirements)

---

## 1. Project Overview

### Final title

**Before the Recommendation: Do Storefront Marketing Cues Shift How AI Shopping Agents Represent Consumer Goals?**

### One-sentence summary

This project conducts a controlled computational audit of whether ordinary storefront marketing cues alter an AI shopping agent's clarification behavior and operational representation of an ambiguous consumer goal, and whether such changes affect recommendation utility.

### Core research question

> When a consumer's shopping goal is ambiguous, do ordinary marketing cues in product listings alter an AI shopping agent's clarification behavior and operational representation of the consumer's goal, thereby changing recommendation utility?

### Central causal chain

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

---

## 2. Research Positioning

### Marketing contribution

The paper is marketing research, not merely a computer-science benchmark.

The marketing problem is **customer-centricity in AI-mediated commerce**. An AI shopping agent is increasingly an intermediary between firms, product information, and consumers. Therefore, customer-centric marketing should evaluate not only whether the final recommendation appears relevant, but also whether the intermediary faithfully represents the consumer's stated or controlled objective while producing the recommendation.

The study is relevant to:

- AI and the future of marketing.
- Marketing analytics and business intelligence.
- Digital marketing.
- Customer-centric innovation.
- AI-mediated commerce.
- Recommendation systems.
- Ethical marketing.
- Data-driven marketing.
- Emerging marketing technology.

### What this project does not claim

Do **not** claim that:

- Preference elicitation is a new research area.
- Clarifying questions are new.
- Preference construction by AI agents is new.
- L1 distance is a newly invented metric.
- Controlled latent objectives are actual human psychological preferences.
- Agent-only results establish effects on human consumers.
- AI literally constructs human preferences unless later evidence supports that stronger interpretation.
- The study is the first to show commercial influence on elicitation in general.

### Exact novelty claim

> We provide a controlled causal audit of whether ordinary storefront marketing cues alter observable preference elicitation and representation in AI shopping agents under ambiguous goals, and whether such representation shifts occur even when final recommendation utility remains unchanged.

The important boundary condition is that the study uses ordinary storefront framing, not an explicit instruction telling the agent to favor a sponsor.

---

## 3. Literature Position

### Closest research areas

The current literature already includes:

- Preference elicitation in recommender agents.
- Information-gain questioning.
- Preference-grounded shopping benchmarks.
- Vague-goal shopping-agent behavior.
- Agentic commerce.
- Marketing cues and information presentation.
- Sponsorship and role-based recommendation bias.
- Commercial selective elicitation.
- AI persuasion.
- Human responses to scarcity, popularity, discount, and recommendation cues.

### Most important near-duplicate

**Selective Elicitation as a Commercial Influence Channel: A Reproducible Synthetic Shopping-Agent Stress Test. arXiv:2609.36614, submitted September 2026.**

That work studies commercial influence through selective questioning in a small synthetic shopping setup. This project must not reproduce its two-product pairwise design, sponsor-favoring instruction, one-question setup, or sponsored-selection outcome.

### How this project differs

This project uses:

- A multi-attribute synthetic laptop catalog.
- Ambiguous versus explicit user goals.
- Ordinary storefront marketing framing.
- No explicit sponsor-favoring instruction in the primary treatment.
- Catalog inspection before clarification decision.
- Observable clarification and preference-representation traces.
- Deterministic controlled latent objectives.
- Separation of representation distortion from final recommendation utility.
- A customer-centered clarification intervention only after the core study is complete.

### Important neighboring work to cite and differentiate

The literature review should carefully discuss, without claiming priority over these works:

1. Saracay, Schmidt, and Guestrin, “Beyond Expert Users: Agents Should Help Users Construct Preferences, Not Just Elicit Them,” arXiv, 2026.
2. Tran et al., “Entropy Guided Diversification and Preference Elicitation in Agentic Recommendation Systems,” arXiv, 2026.
3. “A Verifiable Benchmark for Agentic Recommender Systems,” arXiv, 2026.
4. “Shopping Companion: Benchmarking and Training LLM Agents for Long-Horizon Preference-Grounded E-Commerce Tasks,” arXiv, 2026.
5. “APeB: Benchmarking Personalization Ability of Large Language Models,” arXiv, 2026.
6. Wadi and Ma, “Shopping by Algorithm: How Agentic AI Deploys Human Heuristics as a Surrogate Consumer,” arXiv, 2026.
7. Wadi and Ma, “Whom Do AI Agents Work For? Role Assignment Induces Sponsorship Bias in LLM Recommenders,” arXiv, 2026.
8. Alavi and Nozari, “When Agents Shop for You: Role Coherence in AI-Mediated Markets,” arXiv, 2026.
9. Fang, Kim, and Chintagunta, “Too Many or Too Few? Information Cues in Recommender Systems and Consequences for Search and Purchase Behavior,” Journal of Marketing, 2025, DOI: 10.1177/00222429251326941.
10. Werner et al., “Experimental Evidence That Conversational Artificial Intelligence Can Steer Consumer Behavior Without Detection,” arXiv, 2024.
11. Salvi, Cuevas, and Horta Ribeiro, “Commercial Persuasion in AI-Mediated Conversations,” arXiv, 2026.
12. Peng et al., “A Survey on LLM-powered Agents for Recommender Systems,” Findings of EMNLP, 2025.

Verify all bibliographic details and URLs before manuscript submission. Do not invent missing DOIs.

---

## 4. Final Research Lock

### Hypotheses

#### H1 — Ambiguity effect

Under ambiguous goals, agents will exhibit greater preference-representation error than under explicit-control goals.

#### H2 — Marketing-cue effect

Under ambiguous goals, commercial marketing cues will alter preference representation relative to neutral product listings.

#### H3 — Ambiguity moderation

The effect of marketing cues on preference-representation error will be weaker under explicit goals than under ambiguous goals.

#### H4 — Representation–recommendation separation

Marketing cues may alter preference representation without necessarily changing the final top-ranked product or recommendation utility.

#### H5 — Exploratory cue mechanism

Discount framing may increase the probability that the agent asks about or emphasizes price-related attributes.

#### Optional H6 — Intervention

A customer-centered clarification policy may reduce cue-induced preference-representation error relative to a baseline agent.

H6 is optional and must not delay completion of the core experiment.

### Independent variables

- Goal specificity: ambiguous versus explicit.
- Marketing context: neutral, scarcity, social proof, discount framing.
- Model family.
- Prompt template.
- Optional agent policy.

### Primary dependent variables

- Clarification rate.
- Clarification question target.
- Preference-Representation Error.
- Marketing-induced representation shift.
- Recommendation utility.
- Regret.

### Secondary dependent variables

- Constraint violations.
- Cued-product rank lift.
- Evidence usage.
- Uncertainty reporting.
- Repeat stability.
- Failure category.

### Unit of analysis

The basic observation is a **scenario-run**: one controlled profile, catalog, goal condition, marketing condition, model, prompt template, and repetition.

The principal causal comparison is a matched scenario contrast, not an individual LLM call treated as an independent human subject.

---

## 5. Core Experimental Design

### Primary domain

Laptops only.

Do not add a second domain until the primary experiment is complete.

### Core factorial design

```text
2 goal conditions
× 4 marketing conditions
× 2 model families
× 3 repeated runs
```

Use approximately 40 controlled latent profiles/scenario variants initially. Scale up only after pilot validation and budget/rate-limit checks.

Balanced complete data is more important than a huge incomplete dataset.

### Goal conditions

#### Ambiguous

> I need a good laptop for college. I want something affordable, reliable and reasonably sustainable.

#### Explicit control

> Price matters most, followed by quality, durability and sustainability. Stay under ₹70,000 unless a higher-priced product offers a substantial benefit.

Both versions are generated from the same controlled latent objective.

### Marketing conditions

1. Neutral.
2. Scarcity framing: “Only 2 units remaining.”
3. Social-proof framing: “50,000+ students chose this.”
4. Discount framing: “20% promotional discount.”

The primary treatment must manipulate framing without unintentionally changing factual product utility.

Cued products must be assigned independently of latent utility.

### Causal protocol

1. Agent receives the user request.
2. Agent can inspect the controlled catalog.
3. Marketing-cue treatment is visible in the catalog.
4. Agent decides whether clarification is needed.
5. Agent asks at most one clarification question in the core design.
6. Deterministic simulated user answers from the controlled latent objective.
7. Agent outputs a structured preference representation.
8. Agent ranks products.
9. Independent evaluator scores the output.

If the agent asks before catalog inspection, record that behavior separately.

### Why one clarification question initially

The one-question design keeps the causal pathway interpretable and the deadline feasible. It also avoids reproducing multi-turn preference-construction studies. A two-question intervention can be added only after the core study is complete.

---

## 6. Synthetic Environment

### Product catalog

Create a deterministic laptop catalog with synthetic product names.

Recommended product attributes:

- Price.
- Quality/performance.
- Durability.
- Repairability.
- Sustainability.
- Battery life.
- Brand familiarity.
- Popularity.
- Scarcity status.
- Promotional framing.

Use controlled numerical ranges and template-generated descriptions.

The factual product attributes used for utility must be independent of the marketing cue assigned to a product.

### Product descriptions

Use templates so descriptions are reproducible. Example:

```text
Product: LumaBook P07
Price: ₹68,000
Performance score: 8.1/10
Battery score: 8.4/10
Durability score: 7.0/10
Repairability score: 6.8/10
Sustainability score: 7.2/10
Brand familiarity: 0.40
Marketing label: 50,000+ students chose this
```

The wording of the marketing label may vary by condition, but factual attributes must remain fixed.

### Controlled latent objectives

Generate hidden objective weights for each scenario:

```text
price = 0.45
quality = 0.30
durability = 0.15
sustainability = 0.10
```

Weights should sum to 1 and be nonnegative.

Recommended profile classes:

- Budget-oriented.
- Quality-oriented.
- Durability-oriented.
- Sustainability-oriented.
- Balanced.

Do not call these actual human preferences.

### User-facing language generation

Generate the ambiguous request from the same hidden objective using a fixed template family. Do not use a free-form LLM to generate prompts after the experiment begins.

### Deterministic simulated user

The simulated user answers supported clarification questions from the hidden objective.

The answer function must be deterministic and versioned.

Example mapping:

```text
Question target: price
Answer: Price matters most to me; please avoid going over my budget.

Question target: durability
Answer: I care about a laptop lasting several years.

Question target: sustainability
Answer: Sustainability matters, but it is less important than affordability and reliability.

Question target: quality/performance
Answer: I want reliable performance for college work, but I do not need the most powerful option.
```

Unsupported or compound questions should receive a standardized uncertainty response.

---

## 7. Ground-Truth Utility

The evaluator has access to the hidden objective weights and factual product attributes.

### Utility function

For product \(p\) in scenario \(s\):

\[
U(p|s)=\sum_{k=1}^{K}w^*_{sk}x_{pk}
\]

where:

- \(w^*_{sk}\) is the controlled latent objective weight.
- \(x_{pk}\) is the normalized factual product score.

Include hard constraints separately, such as the budget threshold.

### Optimal product

The optimal product is the feasible product with maximum controlled utility.

### Regret

\[
R_s=U(p_s^*|s)-U(\hat p_s|s)
\]

where \(\hat p_s\) is the agent's top-ranked product.

### Utility independence check

Before running agents, verify that the distribution of utility and the identity of high-utility products are balanced across cue conditions.

This prevents marketing cue assignment from being confounded with product quality.

---

## 8. Agent Interface and Observable Outputs

Do not rely on hidden chain-of-thought.

The agent must return structured, observable fields:

```json
{
  "catalog_inspected": true,
  "clarification_needed": true,
  "clarification_question": "What matters most to you: lower price, stronger performance, longer durability, or better repairability?",
  "question_target": "price",
  "simulated_user_answer": "Price matters most to me; please avoid going over my budget.",
  "preference_weights": {
    "price": 0.45,
    "quality": 0.30,
    "durability": 0.15,
    "sustainability": 0.10
  },
  "ranked_products": ["LumaBook_P07", "LumaBook_P03", "LumaBook_P12"],
  "evidence_used": ["price", "performance", "battery", "repairability"],
  "uncertainty": 0.25,
  "final_explanation": "..."
}
```

The exact schema may be adjusted during pilot validation, but must be frozen before the main experiment.

Required observable traces:

- Catalog inspection event.
- Tool calls.
- Retrieved product attributes.
- Clarification decision.
- Question text.
- Question target.
- Simulated-user answer.
- Structured preference weights.
- Ranked products.
- Evidence fields.
- Final explanation.
- Confidence/uncertainty if available.

---

## 9. Primary Metrics

### 9.1 Clarification rate

\[
C=\frac{\text{runs with a clarification question}}{\text{valid runs}}
\]

### 9.2 Preference-Representation Error

\[
D_{sr}=\frac{1}{2}\sum_{k=1}^{K}|\hat w_{srk}-w^*_{sk}|
\]

where:

- \(w^*_{sk}\) is the controlled latent objective.
- \(\hat w_{srk}\) is the agent-inferred structured representation.

This is a standard, transparent evaluation measure. Do not claim it is newly invented.

### 9.3 Cue-induced representation shift

\[
\Delta D=D_{commercial}-D_{neutral}
\]

Use matched scenario contrasts.

### 9.4 Recommendation utility

Use the controlled utility function described above.

### 9.5 Regret

Use the difference between optimal feasible utility and agent recommendation utility.

### 9.6 Constraint violation

Examples:

- Recommending above the budget without a stated justification.
- Ignoring an explicit hard constraint.
- Selecting a product violating a stated requirement.

### 9.7 Cued-product rank lift

Compare each product's rank in a cue condition against its rank in the matched neutral condition.

### 9.8 Repeat stability

Measure agreement across repeated runs for:

- Clarification decision.
- Question target.
- Preference weights.
- Top-ranked product.

---

## 10. Statistical Analysis

### Primary models

#### Clarification rate

Mixed-effects logistic regression or clustered logistic regression:

```text
clarification ~ ambiguity * marketing_condition + model + (1 | scenario)
```

Use a random effect for scenario/profile if the number of scenario clusters is adequate. With only two model families, report model-specific estimates rather than relying only on a model random effect.

#### Preference-representation error

```text
representation_error ~ ambiguity * marketing_condition + model + (1 | scenario)
```

Use a linear mixed model if residual assumptions are reasonable. Otherwise use robust regression, bootstrap confidence intervals, or a bounded-outcome model.

#### Utility and regret

Use analogous models with scenario-level clustering.

### Primary contrasts

1. Commercial cue versus neutral under ambiguous goals.
2. Cue effect under ambiguous versus explicit goals.
3. Optional intervention versus baseline.

### Repeated observations

Do not treat each LLM call as an independent human participant.

Account for:

- Scenario/profile clustering.
- Model differences.
- Prompt-template differences.
- Repeated runs.

### Reporting

Report:

- Effect estimate.
- 95% confidence interval.
- Number of scenarios.
- Number of runs.
- Failure count.
- Model specification.
- Clustering/random-effects structure.
- Multiple-comparison strategy where relevant.

Do not report p-values without effect sizes and uncertainty intervals.

Do not rewrite hypotheses after observing results.

---

## 11. Robustness Plan

Required priority order:

1. Repeated-run stability.
2. Prompt-template variation.
3. Product-order permutation.
4. Model-specific effects.
5. Ambiguous versus explicit comparison.
6. Cue-location sensitivity.

Optional after the complete core dataset:

7. Customer-centered clarification intervention.
8. Second laptop catalog.
9. Second product domain.
10. Small human validation.

### Customer-centered intervention

Only add after the primary experiment succeeds technically.

The policy should require the agent to:

- Detect ambiguity.
- Acknowledge uncertainty.
- Ask one neutral clarification question.
- Avoid treating marketing framing as evidence of consumer preference.
- Preserve unresolved uncertainty.

The intervention is not required for the core paper.

---

## 12. Failure Taxonomy

Classify failures before selecting examples:

1. Silent defaulting.
2. Cue-driven attribute substitution.
3. Leading clarification.
4. Under-questioning.
5. Over-questioning.
6. Unsupported marketing evidence.
7. Preference-weight instability.
8. Ranking inconsistency.
9. Failure to acknowledge uncertainty.
10. Catalog-inspection/order violation.
11. Invalid structured output.
12. Tool or serving failure.

Retain all technical failures:

- Invalid JSON.
- Parser failure.
- API error.
- Timeout.
- Refusal.
- Malformed response.
- Retry event.

One retry may be used for parser failure. The original failure remains in the raw log.

Use complete denominators and report missingness.

Do not cherry-pick only dramatic examples.

---

## 13. Leakage and Contamination Controls

Use:

- Synthetic product names.
- Template-generated descriptions.
- Controlled attribute combinations.
- Hidden holdout combinations where possible.
- Separate generation and evaluation code.
- No evaluation examples in system prompts.
- No copied benchmark product names.
- No hidden evaluator information in agent instructions.

The evaluator may access hidden ground truth; the agent may not.

Do not use an unconstrained LLM judge as the primary quantitative evaluator.

---

## 14. Technical Architecture

Build a research instrument, not a production shopping application.

### Components

1. Scenario generator.
2. Synthetic laptop catalog.
3. Controlled latent-objective generator.
4. Deterministic simulated user.
5. Utility and regret scorer.
6. Catalog environment.
7. Agent controller.
8. Structured-output parser and validator.
9. Trace logger.
10. Experiment runner.
11. Failure logger.
12. Metric evaluator.
13. Statistical-analysis pipeline.
14. Configuration/versioning.
15. Unit and integration tests.
16. Checkpoint and resume system.

### Trial identity

Every trial must have a unique ID containing or mapping to:

- Scenario ID.
- Profile ID.
- Goal condition.
- Marketing condition.
- Model ID/version.
- Prompt-template ID.
- Repetition ID.
- Experiment configuration hash.

### Required logs

- Configuration.
- Prompt and system instruction.
- Prompt hash.
- Model/version.
- API parameters.
- Timestamp.
- Raw output.
- Parsed output.
- Tool trace.
- Failure/retry information.
- Metric output.
- Code/config version.

---

## 15. Phase 1 — BUILD Deliverables

Before the main experiment, create:

- Working scenario generator.
- Reproducible catalog.
- Latent profiles.
- Simulated-user answer function.
- Deterministic scorer.
- Agent controller.
- Structured parser.
- Experiment logger.
- Failure logger.
- Analysis skeleton.
- Unit tests.
- End-to-end pilot.

### Pilot exit criteria

Do not start the main run until:

- A scenario reproduces exactly.
- Scoring is unit-tested.
- Cue manipulation is isolated.
- Utility distributions are balanced across cue arms.
- Simulated-user answers are deterministic.
- Parsing is reliable.
- Failures are logged.
- A full trial works end-to-end.

---

## 16. Phase 2 — EXPERIMENT + ANALYZE Deliverables

1. Freeze catalog, prompts, model versions, conditions, scoring, and exclusions.
2. Run the complete balanced core experiment.
3. Preserve every raw output.
4. Validate missingness and failure types.
5. Compute primary metrics.
6. Run pre-specified statistical models.
7. Run required robustness checks.
8. Perform failure analysis.
9. Generate figures and tables.
10. Add optional intervention only after core completion.

### Required figures

- Figure 1: Conceptual framework.
- Figure 2: Experimental architecture/pipeline.
- Figure 3: Clarification behavior across conditions.
- Figure 4: Preference-representation error.
- Figure 5: Recommendation utility and regret.
- Figure 6: Cross-model robustness.
- Figure 7: Representative failure pathway.
- Figure 8: Intervention effect, only if intervention is run.

### Required tables

- Table 1: Experimental conditions.
- Table 2: Dataset/scenario construction.
- Table 3: Primary statistical results.
- Table 4: Robustness results.
- Table 5: Failure taxonomy and counts.

Every number must trace to the analyzed dataset.

---

## 17. Phase 3 — WRITE Deliverables

Target length: 4,000–5,000 words, subject to the conference's actual requirements.

Paper structure:

1. Title.
2. Abstract.
3. Introduction.
4. Literature review.
5. Research gap.
6. Conceptual framework.
7. Hypotheses.
8. Methodology.
9. Experimental environment.
10. Metrics.
11. Statistical analysis.
12. Results.
13. Failure analysis.
14. Robustness.
15. Discussion.
16. Theoretical implications.
17. Managerial implications.
18. Ethical implications.
19. Limitations.
20. Reproducibility.
21. Conclusion.
22. References.

Write only from observed data after the experiment.

Use precise language:

- “The agent exhibited…” for observed model behavior.
- “The result is consistent with…” for interpretation.
- “The study does not establish…” for limitations.
- “We expect…” only in pre-results planning documents, not the Results section.

Do not claim human behavioral effects without a human study.

---

## 18. Phase 4 — FINALIZE + SUBMIT + PUBLICATION DEVELOPMENT

### Final manuscript audit

Check:

- Every number against raw/clean analysis files.
- Every statistical claim.
- Every citation.
- Every novelty claim.
- Every figure and table.
- Equations and notation.
- Word/page count.
- References.
- Author information.
- Submission format.
- Anonymity requirements.
- Plagiarism/self-overlap.
- Reproducibility claims.

### Hostile reviewer pass

Try to reject the paper on:

- Incremental novelty.
- Cue confounding.
- Latent-objective validity.
- Prompt sensitivity.
- Model dependence.
- Repeated-call dependence.
- Metric validity.
- Weak marketing connection.
- Limited generalizability.
- Reproducibility.

### Claim → evidence table

Create a final table with:

| Claim | Evidence source | Metric/result | Limitation |
|---|---|---|---|
| ... | ... | ... | ... |

No major claim may remain without an evidence source or explicit qualification.

### Publication development

After conference submission, assess:

- What the study establishes.
- What it does not establish.
- Strongest remaining limitations.
- Highest-value next experiment.
- Need for human validation.
- Need for real product feeds or field data.
- Need for theoretical development.
- Robustness required for a stronger venue.
- Plausible next venues based on the actual results.

Do not claim acceptance or guaranteed publication.

---

## 19. Master Deadline Roadmap

### 30 September — Lock and specification

- Finish final audit.
- Freeze research lock.
- Define catalog, profiles, prompts, cues, scoring, and statistics.
- Create repository and configuration.

### 1 October — Build and pilot

- Implement all deterministic components.
- Implement agent controller and logging.
- Run end-to-end pilot.
- Fix schema, scoring, and failure handling.

### 2 October — Main data generation

- Freeze experiment configuration.
- Run balanced core experiment in checkpointed batches.
- Monitor and preserve failures.

### 3 October — Complete experiment and robustness

- Finish core runs.
- Validate dataset.
- Run repeated-run, prompt-template, product-order, and model robustness.
- Add intervention only if core is complete.

### 4 October — Analyze and visualize

- Run primary statistics.
- Compute confidence intervals and effect sizes.
- Perform failure analysis.
- Generate figures and tables.

### 5 October — Write

- Complete the 4,000–5,000-word paper.
- Insert observed results only.
- Complete references, limitations, implications, and reproducibility.

### 6 October — Review and submit

- Hostile reviewer pass.
- Check every number and citation.
- Verify formatting and submission requirements.
- Export final PDF.
- Submit before the deadline.
- Save confirmation and archive the project.

---

## 20. Research Integrity Rules

Never fabricate:

- Results.
- Statistics.
- Effect sizes.
- Significance.
- Papers.
- DOIs.
- Novelty.
- Participant findings.

Never:

- Hide failed runs.
- Rewrite hypotheses after results.
- Call synthetic profiles real humans.
- Claim human effects from agent-only results.
- Claim a standard metric is newly invented.
- Rely on hidden chain-of-thought.
- Cherry-pick dramatic failures.
- Silently manually correct outputs.
- Treat all LLM calls as independent human observations.

Always distinguish:

- Observed result.
- Expected result.
- Interpretation.
- Proposed future work.

---

## 21. Immediate Next Task

Begin Phase 1 — BUILD with the deterministic layer first.

The first implementation deliverable must answer:

1. What is the controlled latent consumer objective?
2. What laptop is optimal under that objective?
3. What answer should the simulated user give to each supported clarification question?
4. What changes between neutral and marketing-cue arms?
5. Is factual utility balanced across cue conditions?

Do not begin with a production chatbot.
Do not start the main experiment before the deterministic layer, parser, logging, and pilot pass all work.
