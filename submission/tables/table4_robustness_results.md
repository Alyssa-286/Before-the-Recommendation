**Table 4. Robustness results**

| Check | Outcome / model | Result | Runs |
|---|---|---|---|
| Repeat stability | Gemini 3.1 Flash-Lite | clarification agree 0.73; top product agree 0.68; weight spread mean 0.060 | core |
| Repeat stability | Ministral 14B | clarification agree 0.81; top product agree 0.58; weight spread mean 0.051 | core |
| Robust: alternate template | Clarification rate | 0.203 [0.104, 0.292] | 311/320 valid |
| Robust: alternate template | Representation error D | -0.001 [-0.007, 0.004] | 311/320 valid |
| Robust: alternate template | Recommendation utility | -0.001 [-0.007, 0.005] | 311/320 valid |
| Robust: alternate template | Regret | 0.001 [-0.005, 0.007] | 311/320 valid |
| Robust: product order | Clarification rate | -0.012 [-0.065, 0.054] | 303/320 valid |
| Robust: product order | Representation error D | -0.004 [-0.013, 0.005] | 303/320 valid |
| Robust: product order | Recommendation utility | 0.010 [-0.002, 0.022] | 303/320 valid |
| Robust: product order | Regret | -0.010 [-0.022, 0.002] | 303/320 valid |
