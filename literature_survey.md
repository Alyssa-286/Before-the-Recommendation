# Literature Survey (Lite)

**Project:** Before the Recommendation: Do Storefront Marketing Cues Shift How AI Shopping Agents Represent Consumer Goals?

Scope: the immediate research neighbourhood of a controlled audit of AI shopping agents. All 16 works below were verified against the arXiv API or Crossref (`references/verified_references.json`). Summaries are based on the works' official abstracts (`references/arxiv_abstracts.xml`) or bibliographic records. No unverified work is cited.

## 1. Constructed preferences and decision aids (marketing foundations)

- **Bettman, Luce & Payne (1998), *Journal of Consumer Research* 25(3), 187–217.** Consumer preferences are often *constructed* during choice rather than retrieved, and depend on task and context. This is the theoretical basis for treating an agent's preference representation as something that a storefront context could shape.
- **Häubl & Trifts (2000), *Marketing Science* 19(1), 4–21.** Interactive decision aids in online shopping change both search effort and decision quality. This is early evidence that the intermediary between a consumer and a catalog matters for outcomes.

## 2. Marketing cues and information presentation

- **Lynn (1991), *Psychology & Marketing* 8(1), 43–57.** A quantitative review of commodity theory: scarcity increases perceived value. This motivates the scarcity arm ("Only 2 units remaining").
- **Fang, Kim & Chintagunta (2025), *Journal of Marketing* 90(1), 9–28.** The number of information cues a recommender displays changes consumers' search and purchase behaviour. Cue presentation is a marketing lever even when product facts are fixed.

## 3. LLM-based recommendation and agentic recommender systems

- **Peng et al. (2025), arXiv:2502.10050.** A survey of LLM-powered agents for recommender systems. It organizes the field into recommender-oriented, interaction-oriented and simulation-oriented approaches.
- **Narasimhan & Narasimhan (2026), τ-Rec, arXiv:2606.10156.** A benchmark for agentic recommenders that replaces LLM-as-judge scoring with verifiable rewards over catalog predicates. Our deterministic, non-LLM evaluator follows the same principle.
- **Yu et al. (2026), Shopping Companion, arXiv:2603.14864.** A benchmark for long-horizon, preference-grounded e-commerce tasks over more than 1.2 million real items. It identifies preference hallucination and insufficient attribute verification as failure sources.
- **Yang et al. (2026), APeB, arXiv:2607.03162.** A benchmark for personalized product search under raw, underspecified queries. Agents handle explicit queries well but struggle with early-stage intents, which parallels our ambiguous-versus-explicit manipulation.

## 4. Preference elicitation and clarification

- **Saracay, Schmidt & Guestrin (2026), arXiv:2606.30863.** Agents should help users *construct* preferences, not just elicit them, because users often lack the domain knowledge to answer clarifying questions. This is directly relevant to our finding that agents asked trade-off questions a simple simulated user could not answer.
- **Tran et al. (2026), arXiv:2603.11399.** Entropy-guided elicitation selects clarifying questions by expected information gain and carries residual uncertainty into ranking and diversification.

## 5. Commercial influence, persuasion and AI intermediaries

- **Li (2026), arXiv:2609.36614.** In a two-product synthetic task, an *explicit* commercial instruction to ask a targeted question raised sponsored selection and reduced utility, whereas a soft instruction changed no selections. This is the closest prior work. We differ by using ordinary storefront labels with no instruction, a 20-product multi-attribute catalog, an ambiguity manipulation, and representation outcomes measured separately from utility.
- **Wadi & Ma (2026a), arXiv:2609.28372.** In "Tool-Lab" process tracing across eight LLMs, pricing cues rarely mislead at zero information cost. Under acquisition costs, however, a vague goal prompt leads agents to omit diagnostic attributes and make heuristic, suboptimal choices.
- **Wadi & Ma (2026b), arXiv:2609.17989.** Assigning the platform rather than the traveller as the agent's principal attenuates the penalty agents apply to sponsored listings.
- **Alavi & Nozari (2026), arXiv:2604.26220.** Verbal consumer profiles given to a buyer agent let sellers infer willingness to pay ("role coherence"), a form of preference leakage.
- **Werner et al. (2024), arXiv:2409.12143.** A behavioural experiment in which conversational AI shifted human consumer preferences without detection.
- **Salvi, Cuevas & Horta Ribeiro (2026), arXiv:2604.04263.** Two preregistered experiments (N = 2,012) in which LLM-driven promotion nearly tripled selection of sponsored products relative to search placement, and most participants did not detect it.

## 6. Customer-centricity in AI-mediated commerce: synthesis and gap

Together these works show three things:
1. Preferences are context-constructed.
2. Cue presentation affects human choice.
3. Agents can be steered by instructions, roles and information-acquisition costs.

None of them isolates whether *ordinary* storefront labels, with factual attributes held identical and no steering instruction, change how an agent *represents* an ambiguous consumer goal, as distinct from what it finally recommends. Customer-centric evaluation of AI intermediaries needs that separation. Our audit supplies it in a controlled synthetic environment. It finds no shift in represented goals, cue-dependent clarification and choice in one model family, and a strong effect of goal explicitness. Field data and human validation remain open (see `artifacts/publication_development_memo.md`).
