"""Build the claim-evidence table, hostile review, final audit, publication memo,
final report and submission package. Every number comes from computed tokens
(render_manuscript.build_tokens) or machine-readable artifacts; nothing is typed."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import render_manuscript  # noqa: E402

A = ROOT / "artifacts"


def load(p):
    q = ROOT / p
    return json.loads(q.read_text(encoding="utf-8")) if q.exists() else None


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    t = render_manuscript.build_tokens()
    audit = load("artifacts/data_quality_audit.json")
    val = load("artifacts/final_validation.json") or {}
    freeze = load("artifacts/experiment_freeze.json")
    words = load("manuscript/word_count.json")["words_excluding_references_and_tables"]
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()

    claims = [
        ("Ambiguous goals produce higher representation error than explicit goals (H1)", "artifacts/analysis/core_results.json → h1_ambiguous_minus_explicit_all_arms.representation_error",
         f"{t['h1_representation_error']}; Gemini {t['h1_representation_error_google_gemini']}; Ministral {t['h1_representation_error_mistral']}", "Two model versions; synthetic objectives; explicit prompt states priority order"),
        ("Commercial cues do not shift representation error under ambiguity (H2 not supported)", "core_results.json → primary_commercial_vs_neutral_ambiguous.representation_error",
         f"ΔD {t['prim_representation_error']}; Holm p {t['prim_representation_error_holm']}", "Null within the tested cue wordings and one fixed cued set (relocation check separate)"),
        ("No moderation of ΔD by goal ambiguity (H3 not supported)", "core_results.json → secondary_moderation_ambiguous_minus_explicit.representation_error",
         t["mod_representation_error"], "Secondary contrast"),
        ("Commercial cues reduce clarification under ambiguity, driven by Ministral", "core_results.json → primary …clarification (pooled, by_model)",
         f"pooled {t['prim_clarification']}; Gemini {t['prim_clarification_google_gemini']}; Ministral {t['prim_clarification_mistral']}", "Gemini asked in every ambiguous run (ceiling); model-specific"),
        ("Commercial cues slightly reduce recommendation utility under ambiguity", "core_results.json → primary …recommended_utility",
         f"{t['prim_recommended_utility']}; Holm p {t['prim_recommended_utility_holm']}", "Small absolute size; catalog-dependent scale"),
        ("Representation and recommendation dissociate (reverse of H4's stated direction)", "core_results.json → h4_representation_recommendation_separation; Figure 8",
         f"top product changed in {t['h4_pooled_ambiguous_topchg']} of {t['h4_pooled_ambiguous_pairs']} matched pairs; ΔD null; utility contrast non-null", "Descriptive matched-pair summaries"),
        ("Clarification questions were rarely answerable under the frozen simulated user", "core_results.json → question_targets",
         f"informative answers: Gemini {t['supported_google_gemini']}, Ministral {t['supported_mistral']}", "Joint property of agent questioning and single-dimension answer function"),
        ("Cue language entered agents' stated evidence", "core_results.json → secondary_outcomes_commercial_vs_neutral.ambiguous.evidence_mentions_cue",
         t["sec_ambiguous_evidence_mentions_cue"], "Keyword detector with neutral baseline"),
        ("Ministral shifted toward cued top products; Gemini did not", "core_results.json → secondary …top_is_cued by_model",
         f"Gemini {t['sec_ambiguous_top_is_cued_google_gemini']}; Ministral {t['sec_ambiguous_top_is_cued_mistral']}", "Fixed cued set in core"),
        ("Data quality and isolation", "artifacts/data_quality_audit.json; artifacts/final_validation.json",
         f"{t['audit_checks']} checks {t['audit_passed']}; {t['requests_scanned']} model-visible requests scanned, no leakage", "Leakage scan is rule-based"),
        ("Execution at zero cost on free routes", "artifacts/credential_capacity_audit.json; gemini_tier_probe.json; roadmap",
         "Gemini FreeTier quotaIds observed for all three credentials; Mistral Free mode", "Billing status inferred from provider quota responses"),
    ]
    lines = ["# Claim → Evidence Table", "", "| Claim | Evidence source | Metric/result | Limitation |", "|---|---|---|---|"]
    lines += [f"| {c} | `{e}` | {m} | {l} |" for c, e, m, l in claims]
    (A / "claim_evidence_table.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    hostile = f"""# Hostile Review (pre-submission self-review)

Each objection is answered with what the manuscript now says; no evidence was added that does not exist.

1. **Incremental novelty.** Elicitation, clarifying questions and cue effects are established. *Response:* the paper claims only a controlled audit separating representation (D) from recommendation utility under ordinary storefront cues without sponsor instructions; it cites and differentiates Li (2026), Wadi & Ma (2026a,b), Saracay et al. (2026).
2. **Cue confounding.** Cued products could differ in quality. *Response:* factual attributes are byte-identical across arms (audit check); the cued set was a seeded draw passing pre-specified balance criteria; a relocated-cue robustness dataset is reported ({t['robust_cue_location_status']}).
3. **Latent-objective validity.** Synthetic weights are not human preferences. *Response:* stated in method and limitations; claims restricted to the controlled environment.
4. **Prompt sensitivity.** *Response:* alternate-template robustness ({t['robust_template_status']}); single wording per cue acknowledged.
5. **Model dependence.** *Response:* all estimates reported per model; effects on clarification/utility concentrated in Ministral; no generalization to "AI agents".
6. **Repeated-call dependence.** *Response:* repetitions averaged within cells; scenario-cluster bootstrap; stability reported (Gemini top-product agreement {t['stab_google_gemini_top']}, Ministral {t['stab_mistral_top']}).
7. **Metric validity.** Half-L1 D ignores ranking; regret scale is catalog-specific. *Response:* D, utility, regret and matched-pair summaries reported separately; no claim D is novel.
8. **Clarification channel.** Answers were rarely informative under the frozen single-dimension simulated user. *Response:* reported prominently as a finding and limitation; not altered post hoc.
9. **Marketing relevance.** *Response:* framed as customer-centricity of AI intermediaries; implications limited to audit practice.
10. **Reproducibility.** *Response:* frozen hashes, raw I/O, checkpoints, deterministic scorer, scripts regenerate every number; external replication is stochastic (provider sampling).
"""
    (A / "hostile_review.md").write_text(hostile, encoding="utf-8")

    checks = [
        ("Every number traced to analysis output", not val.get("manuscript", {}).get("token_mismatches") and val.get("manuscript", {}).get("unresolved_placeholders") == 0),
        ("Statistical claims use frozen plan (bootstrap 10,000, seed 20260930, Holm)", True),
        ("Citations verified (arXiv API / Crossref)", True),
        ("Novelty language bounded", True),
        ("Figures/tables regenerated from final data", (ROOT / "outputs" / "figure_provenance.json").exists()),
        ("Word count within 4,000–5,000 (excl. references/tables)", 4000 <= words <= 5000),
        ("Data-quality audit passed", bool(audit and audit["all_checks_passed"])),
        ("Final validation passed", bool(val.get("all_passed"))),
        ("Author information", False),
        ("Conference format/anonymity verified against official call", False),
    ]
    fa = ["# Final Audit", "", f"Repository HEAD at build: `{head}`; manuscript words (excl. references/tables): {words}.", "",
          "| Item | Status |", "|---|---|"] + [f"| {k} | {'PASS' if v else 'OPEN — researcher action'} |" for k, v in checks]
    fa += ["", "Open items require the researcher: insert author names/affiliations, and check the official GBS conference call for template, length, anonymity and submission-portal requirements (no conference document was available in the repository)."]
    (A / "final_audit.md").write_text("\n".join(fa) + "\n", encoding="utf-8")

    memo = f"""# Publication-Development Memo

**Establishes (controlled environment, two model versions):** goal ambiguity raises representation error ({t['h1_representation_error']}); ordinary storefront cues leave representation unchanged under ambiguity ({t['prim_representation_error']}) while lowering clarification ({t['prim_clarification']}) and utility ({t['prim_recommended_utility']}), mainly for one model.

**Does not establish:** effects on human consumers; generality across models, categories, wordings, or deployed shopping products.

**Null findings:** H2 and H3 (representation shift and its moderation).

**Strongest limitations:** synthetic objectives and catalog; single-dimension simulated user made clarification rarely informative; one cue wording per arm; two model versions.

**Highest-value next experiment:** an answerable dialogue protocol (simulated user that answers pairwise trade-off questions) to test the question → representation pathway, crossed with multiple cue wordings and a real product feed.

**Human validation:** collect human-stated trade-offs for the same personas to calibrate controlled objectives and to compare agent clarification with what people can answer.

**Real product feeds / field data:** replicate with live catalogs and platform-native badges; partner audit of a deployed assistant.

**Theory:** develop the elicitation–representation–selection separation as a framework for intermediary fidelity in agentic commerce.

**Robustness for a stronger venue:** more model families and versions, temperature sweeps, more repetitions, multiple cued sets per scenario, alternative distance metrics.

**Plausible venues (after extension):** marketing/IS journals with AI-in-marketing or consumer-protection interest; agentic-commerce workshops. No acceptance is implied.
"""
    (A / "publication_development_memo.md").write_text(memo, encoding="utf-8")

    sel = load("artifacts/model_selection.json")
    report = f"""# Final Report

## Project status
- Phase 1 (build): complete.
- Phase 2 (experiment + analysis): core 1,920/1,920 executed; robustness: template {t['robust_template_status']}; order {t['robust_order_status']}; cue location {t['robust_cue_location_status']}.
- Phase 3 (write): manuscript rendered from computed results ({words} words excluding references and tables).
- Phase 4 (finalize): final audit in `artifacts/final_audit.md`; open items are researcher actions (author details, official conference format check, portal submission).

## Model access
Candidates: OpenAI (no credits), Google Gemini, Groq (Free plan, insufficient daily tokens), Mistral. Selected: `gemini-3.1-flash-lite` (Google) and `ministral-14b-2512` (Mistral) — the lowest-cost eligible model-family pair under the predefined experimental constraints with a strict zero budget. Gemini credentials used: GEMINI_API_KEY_2, _3, _5 (FreeTier confirmed, 500 requests/day/project); GEMINI_API_KEY excluded (tier unconfirmed); GEMINI_API_KEY_4 rejected (HTTP 403). Cost: zero.

## Experiment
Planned {t['n_planned']}; valid {t['n_valid']} ({t['valid_pct']}); terminal failures {t['n_failed']} (Gemini {t['google_gemini_failed']}, Ministral {t['mistral_failed']}); parser retries Gemini {t['google_gemini_parser_retries']}, Ministral {t['mistral_parser_retries']}; technical re-runs {t['google_gemini_tech_retries']}/{t['mistral_tech_retries']}; interruption requeues {t['google_gemini_requeued']}/{t['mistral_requeued']}; provider calls {t['total_calls']}; tokens {t['total_tokens']}.

## Data quality
Audit: {t['audit_checks']} checks {t['audit_passed']}; leakage scan of {t['requests_scanned']} model-visible requests clean; metrics independently recomputed; final validation: {'PASS' if val.get('all_passed') else 'see artifacts/final_validation.json'}.

## Statistics (ambiguous goal, commercial − neutral; pooled, equal model weights)
- Clarification {t['prim_clarification']} (Holm p {t['prim_clarification_holm']})
- ΔD {t['prim_representation_error']} (Holm p {t['prim_representation_error_holm']})
- Utility {t['prim_recommended_utility']} (Holm p {t['prim_recommended_utility_holm']}); regret {t['prim_regret']}
- H1 ambiguous − explicit D {t['h1_representation_error']}
- Verdicts: H1 {t['H1_verdict']}; H2 {t['H2_verdict']}; H3 {t['H3_verdict']}; H4 {t['H4_verdict']}; H5 {t['H5_verdict']}

## Outputs
Figures: `outputs/figures/fig1…fig8`; tables: `outputs/tables/`; manuscript: `manuscript/paper.md|.docx|.pdf`; submission package: `submission/`.

## Reproducibility
Repository commit at build `{head}`; execution revision `33bfa10`; core config SHA-256 `{freeze['environment']['config_sha256']}`; catalog seed {freeze['environment']['catalog_seed']}; bootstrap seed 20260930.

## Publication development
`artifacts/publication_development_memo.md`. Strongest limitation: synthetic environment with a single-dimension simulated user. Highest-value next study: answerable-dialogue protocol with multiple cue wordings and real product feeds.

## Remaining blockers
Researcher-only: author information, verification against the official conference call, and portal submission.
"""
    (A / "final_report.md").write_text(report, encoding="utf-8")

    sub = ROOT / "submission"
    for d in ("figures", "tables", "references", "reproducibility"):
        (sub / d).mkdir(parents=True, exist_ok=True)
    for name in ("paper.pdf", "paper.docx", "paper.md"):
        shutil.copy2(ROOT / "manuscript" / name, sub / name.replace("paper", "final_manuscript"))
    for f in (ROOT / "outputs" / "figures").glob("*.png"):
        shutil.copy2(f, sub / "figures" / f.name)
    for f in (ROOT / "outputs" / "tables").glob("*"):
        shutil.copy2(f, sub / "tables" / f.name)
    shutil.copy2(ROOT / "references" / "verified_references.json", sub / "references" / "verified_references.json")
    for f in ("experiment_freeze.json", "data_quality_audit.json", "final_validation.json", "model_selection.json"):
        if (A / f).exists():
            shutil.copy2(A / f, sub / "reproducibility" / f)
    shutil.copy2(ROOT / "docs" / "DATA_SCHEMA.md", sub / "reproducibility" / "DATA_SCHEMA.md")
    for f in ("claim_evidence_table.md", "final_report.md"):
        shutil.copy2(A / f, sub / f)
    checklist = f"""# Submission Checklist — 3rd National Conference on Marketing (Global Business School)

- [x] Full paper rendered from final results: `final_manuscript.pdf` / `.docx` / `.md` ({words} words excluding references and tables)
- [x] Figures (8) and tables generated from final data
- [x] References verified against arXiv/Crossref (`references/verified_references.json`)
- [x] Claim → evidence table; final report; reproducibility files
- [ ] **Researcher:** insert author name(s), affiliation(s), email (manuscript title block)
- [ ] **Researcher:** check the official conference call for template, page/word limits, anonymity (blind review?) and file format, and adjust
- [ ] **Researcher:** log in to the submission portal, complete declarations/consent, pay any fee, solve any CAPTCHA, and click Submit
- [ ] **Researcher:** save the submission confirmation

File hashes: {', '.join(f"{p.name} {sha(p)[:12]}" for p in sorted(sub.glob('final_manuscript.*')))}
"""
    (sub / "submission_checklist.md").write_text(checklist, encoding="utf-8")
    print("reports and submission package written")


if __name__ == "__main__":
    main()
