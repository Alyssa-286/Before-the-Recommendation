**Table 1. Experimental conditions**

| Factor | Levels | Implementation |
|---|---|---|
| Goal condition | Ambiguous; Explicit | Frozen templates ambiguous-v1-01 / explicit-v1-01 rendered from the same latent objective |
| Marketing condition | Neutral; Scarcity; Social proof; Discount | Labels 'Only 2 units remaining.', '50,000+ students chose this.', '20% promotional discount.' on 5 fixed products; facts unchanged |
| Model family | Google Gemini; Mistral | gemini-3.1-flash-lite; ministral-14b-2512 (free routes, provider-default temperature) |
| Repetition | 1–3 | Independent calls of the same cell |
| Scenario/profile | 40 | 5 profile classes × 8 jittered objectives |
| Core runs | 1,920 | 40 × 2 × 4 × 2 × 3 |
