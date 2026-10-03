# Hostile Review (pre-submission self-review)

Each objection is answered with what the manuscript now says; no evidence was added that does not exist.

1. **Incremental novelty.** Elicitation, clarifying questions and cue effects are established. *Response:* the paper claims only a controlled audit separating representation (D) from recommendation utility under ordinary storefront cues without sponsor instructions; it cites and differentiates Li (2026), Wadi & Ma (2026a,b), Saracay et al. (2026).
2. **Cue confounding.** Cued products could differ in quality. *Response:* factual attributes are byte-identical across arms (audit check); the cued set was a seeded draw passing pre-specified balance criteria; a relocated-cue robustness dataset is reported (315 of 320 runs valid; audit passed).
3. **Latent-objective validity.** Synthetic weights are not human preferences. *Response:* stated in method and limitations; claims restricted to the controlled environment.
4. **Prompt sensitivity.** *Response:* alternate-template robustness (311 of 320 runs valid; audit passed); single wording per cue acknowledged.
5. **Model dependence.** *Response:* all estimates reported per model; effects on clarification/utility concentrated in Ministral; no generalization to "AI agents".
6. **Repeated-call dependence.** *Response:* repetitions averaged within cells; scenario-cluster bootstrap; stability reported (Gemini top-product agreement 68.4%, Ministral 57.8%).
7. **Metric validity.** Half-L1 D ignores ranking; regret scale is catalog-specific. *Response:* D, utility, regret and matched-pair summaries reported separately; no claim D is novel.
8. **Clarification channel.** Answers were rarely informative under the frozen single-dimension simulated user. *Response:* reported prominently as a finding and limitation; not altered post hoc.
9. **Marketing relevance.** *Response:* framed as customer-centricity of AI intermediaries; implications limited to audit practice.
10. **Reproducibility.** *Response:* frozen hashes, raw I/O, checkpoints, deterministic scorer, scripts regenerate every number; external replication is stochastic (provider sampling).
