# Domain Eval Packs

Status: active minimum baseline from `MB-172`.

## Purpose

Domain eval packs provide repeatable offline evidence for a promoted route and
its canonical domains. They exercise the real governed Core rather than a
parallel mock architecture.

Each case validates:

- governance decision;
- primary route and canonical domain references;
- workflow profile;
- governed specialist use;
- bounded response evidence;
- memory causality status;
- required observable events and trace health.

## Run The Baseline Pack

```powershell
.\.venv\Scripts\python.exe tools\run_domain_eval.py --format text
```

The default pack is
`tools/benchmarks/datasets/domain_analysis_eval_pack_v1.json`. It runs a seed
analysis and a follow-up in the same mission so the second case must prove
causal memory guidance.

Artifacts are written under `.jarvis_runtime/domain_evals/<run-id>/` unless an
explicit `--output-dir` is provided.

## Interpretation

- `candidate_ready_for_human_review`: every required case passed the configured
  threshold.
- `attention_required`: one or more pack, route, response, memory, specialist
  or trace checks failed.
- `manual_review_only`: evidence is sufficient for review, not promotion.
- `blocked`: the pack cannot support promotion review.

A green eval never sets `promotion_authorized`. Runtime route promotion still
requires explicit human review, registry change, rollback evidence and release
gates.

## Creating Another Pack

Copy the structure of the baseline JSON, use a promoted registry route, match
its complete canonical domain refs, workflow and specialist, and add at least
one case. Packs must remain bounded, local, versioned and `offline_only=true`.
Do not include secrets or full response transcripts in expected evidence.
