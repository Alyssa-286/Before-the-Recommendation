# Data Schema

All files are UTF-8 JSON Lines (one JSON object per line), append-only and flushed/fsynced per record. Line endings are preserved byte-exactly (`data/** -text` in `.gitattributes`). No file contains credential values; credentials appear only as environment-variable **names**.

## Directory layout

```
data/<stage>/<model-dir>/          stage ∈ {core, robust_template, robust_order, robust_cue_location, pilot, pilot_v2, ...}
  checkpoint.sqlite                trial registry + state machine (pending/running/completed/failed) and transition events
  traces.attempt<N>.jsonl          one complete trial trace per line for attempt N (N>1 only after an interruption requeue or technical re-run)
  model_io.attempt<N>.jsonl        one raw provider exchange per line (request payload + raw response bytes)
  failures.jsonl                   every recoverable and terminal failure event
  transport_events.jsonl           HTTP 429/5xx re-sends and daily-quota credential suspensions (no model output)
  credential_requests.jsonl        one line per HTTP request: credential VARIABLE NAME, status, request-body SHA-256
  runner_events.jsonl              per-attempt outcomes and technical-retry scheduling
data/analysis/<stage>_dataset.jsonl  derived trial-level analysis rows (recomputed from traces; never edited by hand)
```

## Raw: trial trace (`traces.attempt<N>.jsonl`, schema `trace.v1`)

| Field | Content |
|---|---|
| `trial_id` | SHA-256 of the canonical `identity` object |
| `identity` | scenario_id, profile_id, goal_condition, marketing_condition, model_family, model_version, repetition, prompt_template_id, experiment_version, config_sha256, random_seed, code_revision |
| `agent_visible` | exactly what the model could see: system_instruction, request_text, prompt_sha256, api_parameters (credential variable name only) |
| `events` | ordered protocol events: `trial_started` (incl. cued_product_ids, listing_order, protocol_variant), `response_received`, `tool_call`, `catalog_inspected` (structured catalog + `model_visible_text`), `simulated_user_answer`, `recommendation_submitted`, `parser_retry_requested`, `recommendation_scored`, `trial_completed` / `trial_failed` |
| `raw.attempts` / `derived.attempts` | every submission attempt with parse status, parsed output and validation errors |
| `derived.metrics` | clarification fields, top product, utility, regret, representation error, constraint flag |
| `evaluator_private` | controlled objective, optimal product/utility, factual-utility balance — **never sent to the model** |
| `failures` | failure events (category, stage, recoverable, detail_code) |

## Raw: provider exchange (`model_io.attempt<N>.jsonl`)

`record_type` (`model_io` or `model_io_failure`), `trial_id`, `call_index`, `provider`, `configured_model_id`, `observed_model_id`, request start/finish timestamps, `latency_ms`, `request_payload` (messages + tools, no headers), `raw_response_base64` (exact bytes), `raw_response_text`, `raw_response_sha256`, `input_tokens`, `output_tokens`, `finish_reason`, `refused`, `tool_calls`, `assistant_text`, `headers_logged: false`.

## Derived: analysis row (`data/analysis/<stage>_dataset.jsonl`, `analysis-dataset-v1.0.0`)

Identity fields; `valid`; `terminal_failure_category/detail`; `trial_attempts`; `parser_retry_used`; token and call counts; `catalog_before_clarification`; `clarification`, `clarification_question`, `question_target_raw/normalized`, `clarification_answer_supported`; `w_hat`, `w_star`; `representation_error` (D); `top_product`, `top_is_cued`, `recommended_utility`, `optimal_utility`, `regret`, `constraint_violated`; `ranked_products`, `cued_mean_rank`; `uncertainty`; `evidence_mentions_cue`; matched-neutral fields (`matched_neutral_trial_id`, `delta_representation_error`, `weight_shift_vs_neutral`, `top_changed_vs_neutral`, `cued_rank_lift`); `cell_weight_spread`; `taxonomy` (12 pre-specified failure flags; operational rules in `src/before_recommendation/dataset.py`).

## Analysis outputs

`artifacts/analysis/<stage>_results.json`: descriptives per model × goal × marketing cell; primary, secondary, moderation, H1, cue-specific and secondary-outcome matched contrasts (pooled with equal model weights and per model; estimate, 95% scenario-bootstrap percentile CI, bootstrap p, Holm-adjusted p where specified, scenario counts); H4 separation summaries; H5; factorial models (coefficients, cluster-robust SEs); repeat stability; failure taxonomy; missingness.
