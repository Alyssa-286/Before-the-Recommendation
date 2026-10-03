# Before the Recommendation: Do Storefront Marketing Cues Shift How AI Shopping Agents Represent Consumer Goals?

[Author name(s) and affiliation — to be completed by the researcher before submission]

## 1. Introduction

Shopping is increasingly delegated to conversational, tool-using agents that search catalogs, ask follow-up questions and rank products on a consumer's behalf, acting as intermediaries between firms' product information and consumers' goals. Customer-centric marketing has always asked whether the offer fits the customer. When an AI agent sits in the middle, a second question appears: does the intermediary *represent* the customer's goal faithfully before it recommends anything?

That question matters most when goals are vague. A student who asks for "a good laptop for college ... affordable, reliable and reasonably sustainable" has not said how these attributes trade off. The agent must either ask, infer or default, and its inference is formed while it reads a storefront. Ordinary storefronts are full of marketing cues: scarcity ("Only 2 units remaining"), social proof ("50,000+ students chose this") and promotional framing ("20% promotional discount"). Decades of marketing research show that such cues shape human evaluation (e.g., Lynn, 1991), and recent experiments show that conversational AI can steer human choice (Werner et al., 2024; Salvi et al., 2026). Much less is known about whether ordinary cues, with no instruction to favour a sponsor, alter how an AI agent *operationalizes* the consumer's goal. That covers whether it asks for clarification, what it asks about, and what preference weights it infers.

This paper reports a controlled computational audit of that question. We built a synthetic laptop storefront in which every consumer goal is a controlled latent objective known only to the evaluator. Two model families (Google's Gemini 3.1 Flash-Lite and Mistral's Ministral 14B) acted as shopping agents in 1,920 pre-specified scenario-runs. The design crosses goal specificity (ambiguous vs explicit) with four storefront conditions (neutral, scarcity, social proof, discount). The protocol forces catalog inspection before any clarification, allows at most one question answered by a deterministic simulated user, and requires a structured preference representation and ranking. A deterministic evaluator then measures the distance between the represented and the controlled objective, and separately the utility and regret of the recommendation.

The contribution is deliberately bounded. Preference elicitation, clarifying questions and preference construction are established topics (Bettman et al., 1998; Saracay et al., 2026; Tran et al., 2026), and the half-L1 distance we use is a standard measure. What this study adds is a controlled causal test of whether *ordinary* storefront framing changes observable elicitation and goal representation under ambiguity. It also separates representation fidelity from final recommendation utility, two quantities that customer-centric evaluation should not conflate. All results describe the tested model versions in a synthetic environment; no human participants were involved.

## 2. Literature Review

**Constructed preferences and decision aids.** Consumer research has long treated preferences as often constructed during choice rather than retrieved (Bettman et al., 1998). Interactive decision aids can therefore change both the process and the outcome of online shopping (Häubl & Trifts, 2000). These ideas have re-entered the agent literature. Saracay et al. (2026) argue that agents should help users *construct* preferences rather than merely elicit them. Tran et al. (2026) use attribute entropy to choose clarifying questions and carry residual uncertainty into ranking.

**Benchmarks for agentic recommendation and shopping.** Several 2026 benchmarks evaluate agents on preference-grounded shopping. τ-Rec replaces LLM-as-judge scoring with verifiable rewards over catalog predicates (Narasimhan & Narasimhan, 2026). Shopping Companion studies long-horizon, cross-session preference memory over real products and identifies preference hallucination as a failure source (Yu et al., 2026). APeB finds that agents handle explicit queries well but struggle with underspecified, early-stage intents (Yang et al., 2026). Peng et al. (2025) survey LLM-powered recommender agents. These works measure task success. Our focus is narrower: whether a marketing context shifts the agent's internal *goal representation*, measured against a known latent objective.

**Marketing cues, information cues and AI intermediaries.** Scarcity increases perceived value in a large commodity-theory literature (Lynn, 1991). Fang et al. (2025) show that the number of information cues shown by a recommender changes consumers' search and purchase behaviour. For AI intermediaries, Wadi and Ma (2026a) trace how pricing cues and vague versus specific goal prompts affect agents' information acquisition and choice. They find that under acquisition costs a vague goal creates a search-mediated vulnerability. Wadi and Ma (2026b) show that assigning the platform as the agent's principal weakens the penalty agents apply to sponsored listings. Alavi and Nozari (2026) show that verbal consumer profiles leak willingness to pay to sellers. Human-subject experiments document conversational steering (Werner et al., 2024) and covert commercial persuasion by LLM agents (Salvi et al., 2026).

**Commercial influence through elicitation.** The most closely related study is Li (2026). It shows in a two-product synthetic task that an explicit commercial instruction to ask a targeted question can raise sponsored selection and reduce utility, whereas a soft instruction changed no selections. We do not reproduce that design. We use a 20-product multi-attribute catalog, no sponsor-favouring instruction, ordinary storefront labels, an ambiguity manipulation, and representation outcomes measured separately from utility.

## 3. Research Gap and Question

Existing work evaluates either final choices and task success or explicit commercial instructions. It does not isolate whether ordinary storefront framing, presented as product-listing labels with no change to facts and no instruction, changes how an agent clarifies and represents an ambiguous goal. Nor does it check whether any such change propagates to recommendation utility. Our research question is:

> When a consumer's shopping goal is ambiguous, do ordinary marketing cues in product listings alter an AI shopping agent's clarification behaviour and operational representation of the consumer's goal, thereby changing recommendation utility?

## 4. Conceptual Framework and Hypotheses

Figure 1 summarises the framework. Goal ambiguity and storefront context jointly enter the agent's catalog inspection and clarification decision. The resulting question and its answer shape the operational preference representation ŵ. The representation drives the ranking, whose top product determines utility and regret. The controlled objective w* drives only the simulated user and the evaluator. The hypotheses were fixed before data collection:

- **H1 (ambiguity effect).** Under ambiguous goals, agents exhibit greater preference-representation error than under explicit goals.
- **H2 (marketing-cue effect).** Under ambiguous goals, commercial cues alter preference representation relative to neutral listings.
- **H3 (ambiguity moderation).** The cue effect on representation error is weaker under explicit goals.
- **H4 (representation–recommendation separation).** Cues may alter representation without necessarily changing the top-ranked product or recommendation utility.
- **H5 (exploratory).** Discount framing may increase the probability of price-related questions.

## 5. Methodology

### 5.1 Experimental environment

The catalog contains 20 synthetic laptops ("LumaBook_P01"–"P20"). Each has a price (₹35,000–95,000) and 0–100 scores for quality, durability, repairability, sustainability, battery life, brand familiarity and popularity. Utility uses four dimensions: price (normalized so cheaper is better), quality, durability and sustainability. Forty controlled latent objectives were generated from five profile classes (budget-, quality-, durability-, sustainability-oriented, balanced), eight per class, with seeded jitter. They are synthetic evaluation targets, not human preferences.

A pre-data audit found that the original Phase-1 catalog draw contained one near-dominant product. It was optimal for all 40 objectives and on 98% of the weight simplex. Scoring and objective generation were independently verified as correct. We therefore committed ten acceptance criteria *before* any search: at least five distinct optima, no product optimal for more than 30% of objectives, cue-assignment balance, identical factual utility across arms, and others. A deterministic seed search accepted the first catalog satisfying all of them (seed 20260955, after 25 rejections). The attribute generator, objectives, cue seed, prompts and hypotheses were unchanged.

### 5.2 Manipulations

*Goal condition.* The ambiguous request is fixed: "I need a good laptop for college. I want something affordable, reliable and reasonably sustainable." The explicit request states the objective's priority order and the ₹70,000 soft reference, e.g., "My priorities, from highest to lowest, are lower price, then strong performance and reliability, then long-term durability, then sustainability. Try to stay under ₹70,000 unless a higher-priced laptop offers a substantial benefit."

*Marketing condition.* In the three commercial arms, the same five products (a seeded draw, balanced on utility rank and price) carry one label: "Only 2 units remaining." (scarcity), "50,000+ students chose this." (social proof) or "20% promotional discount." (discount). Neutral listings carry no label. Factual attributes are byte-identical across arms. The model never sees the arm's name.

### 5.3 Agents and causal protocol

Two distinct model families served as agents: Google `gemini-3.1-flash-lite` and Mistral `ministral-14b-2512`. Both used provider-default sampling and a 4,096-token output limit. They were selected as the lowest-cost eligible pair under a strict zero-budget constraint, using only verified free routes. Each trial follows a fixed tool protocol.
1. The user request arrives.
2. The agent's first action must be `inspect_catalog`, which returns the storefront table with any cue labels.
3. The agent may call `ask_clarification` at most once.
4. A deterministic simulated user answers from w*. A single-dimension question receives a fixed, rank-revealing answer; unsupported or compound questions receive a standard uncertainty answer.
5. The agent calls `submit_recommendation` with preference weights (summing to 1), a ranking, evidence, uncertainty and an explanation.

Order violations are recorded, not repaired. One corrected submission is allowed after a schema failure. A trial whose provider call fails is re-run once in full, and the original attempt is preserved. No hidden chain-of-thought is used as data.

### 5.4 Measures

Representation error is D = ½ Σ_k |ŵ_k − w*_k|, ranging from 0 (identical) to 1. The cue-induced shift ΔD is the matched commercial-minus-neutral difference in D. Utility is U(p) = Σ_k w*_k x_pk of the top-ranked product, and regret is U(p*) − U(top). Clarification rate is the share of valid runs with a question. Secondary measures include question target, cued-product rank, evidence mentioning a cue term, reported uncertainty, repeat stability and a pre-specified failure taxonomy.

### 5.5 Design and statistical analysis

The design is 40 scenarios × 2 goals × 4 marketing conditions × 2 model families × 3 repetitions = 1,920 planned runs. Analysis follows a plan frozen before any live call (analysis-plan v1.0.0). Repetitions are averaged within each scenario-goal-marketing-model cell. "Commercial" is the equal-weight mean of the three cue arms. Model families are fixed comparison groups weighted equally. The primary contrast is commercial minus neutral under ambiguous goals, for clarification (risk difference), D (ΔD), utility and regret. Its 95% intervals come from 10,000 scenario-level paired bootstrap resamples (seed 20260930), which treat the 40 scenarios as clusters. Holm adjustment is applied across the four primary contrasts. Secondary analyses are the explicit-goal contrast, the moderation contrast, cue-specific contrasts, and factorial models (logit for clarification; OLS for continuous outcomes) of the form outcome ~ goal × marketing + model with scenario-clustered standard errors. Repeated calls are never treated as independent human observations.
