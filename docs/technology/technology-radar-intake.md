# Technology radar intake

Status: active baseline from MB-208.

## Purpose

The technology radar records manually reviewed external references as immutable,
versioned evidence. It does not fetch a source, ingest its content, install a
dependency, create an evolution proposal, change priority, activate runtime
behavior or promote anything.

The canonical sequence is:

```text
local manifest -> strict validation -> read-only Knowledge assessment
               -> append-only Evolution registry -> verified operator view
```

An accepted record remains an operator-attested, untrusted reference. The
declared content SHA-256 identifies and binds the source snapshot that the
operator attests was reviewed; it does not claim that JARVIS fetched or
independently verified that snapshot.

## Required manifest

The input is one UTF-8 JSON object, at most 64 KiB, inside an explicitly supplied
local intake root. Duplicate keys, non-finite numbers, unknown or missing fields,
symlinks and traversal outside that root fail closed.

The object maps exactly to `TechnologyRadarIntakeContract` and must include:

- identity: `intake_id`, `candidate_ref`, canonical SemVer `intake_version` and
  optional exact predecessor id/fingerprint;
- source: name, kind (`repository`, `skill`, `standard` or `article`), canonical
  public HTTPS locator, immutable source-version ref and lowercase SHA-256;
- legal and temporal evidence: license id/status/evidence and UTC retrieval time;
- reviewed content: claims, risks, absorption class and target gap refs;
- human review: research approval, review-subject fingerprint, reviewer,
  approved status, review evidence and ordered UTC review/record timestamps;
- fixed safety declarations: read-only/immutable/human-review true and every
  fetch, ingestion, installation, execution, activation, promotion, Core and
  priority authority false.

Before approval, compute `technology_radar_review_subject_fingerprint()` over
the draft contract. The function excludes only the review metadata and
`recorded_at`, so the approval binds the exact source, hash, license, claims,
risks, target gaps, authority declarations and lineage. Reusing a review after
changing any of those fields is rejected.

Manifest fields or source locators containing recognized credentials, private
keys, secret assignments, bearer tokens, sensitive local paths, userinfo,
fragments, sensitive query keys, loopback or private hosts are rejected before
persistence. Prompt-like text may be retained only as inert, untrusted evidence
and is never consumed as instruction or runtime authority.
`source_version_ref` is an operator-declared immutable locator whose canonical
form is checked locally; upstream immutability is not independently verified.

## Operator commands

Register a reviewed local manifest:

```powershell
python -m apps.jarvis_console technology-radar-intake `
  --intake-root .\reviewed-technology-intake `
  --manifest candidate-v1.json `
  --manifest-sha256 <lowercase-sha256-of-reviewed-json>
```

The mutating command intentionally does not support JSON output. Read the
verified registry or filter it without mutation:

```powershell
python -m apps.jarvis_console technology-radar --target-gap-ref KNW-006
python -m apps.jarvis_console technology-radar --source-kind repository --format json
```

An exact retry is idempotent. A divergent payload with the same intake,
candidate/version or canonical source locator/version is a collision. Genesis
is exactly `1.0.0` with no predecessor; every newer version must reference the
exact verified predecessor and advance SemVer.

`license_id=NOASSERTION` is retained only with
`license_status=unknown_requires_review` and an explicit legal risk. It may be
visible in the radar but cannot release a sandbox experiment in MB-209 until
license evidence is resolved.

An eligible, licensed intake can be translated into an inert, paired experiment
pack, but MB-209 resolves and revalidates the exact intake again and grants no
execution or promotion authority. See
[Technology experiment packs](technology-experiment-packs.md) for the manifest,
evaluation and attestation boundaries.

## Integrity and limitations

The Evolution store uses canonical JSON plus SHA-256, append-only constraints,
identity uniqueness and no-update/no-delete triggers. Reads revalidate payload,
columns, source identity, lineage and contract; invalid rows are omitted without
starving older valid records.

Reviewer identity is a local declaration, not a cryptographic signature. Source
hash and license evidence are operator attestations because MB-208 performs no
network retrieval. A privileged actor able to drop database protections and
rewrite both payload and hash is outside the local tamper-evidence guarantee.
Promotion remains a separate human-gated workflow; MB-208 grants none.
