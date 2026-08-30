# Technology Experiment Evidence

This directory contains only bounded, versioned and declarative evidence used by
the technology experiment attestation evaluator.

It must never contain downloaded repositories, packages, executable code,
binaries, dependency locks or credentials. An experiment case describes a fixed
input and the checks expected from a sovereign JARVIS consumer. Baseline and
candidate observations are produced outside this evaluator in a separately
controlled sandbox and submitted as inert attestations.

The evaluator does not prove that an observation producer executed the claimed
experiment. It fingerprints the exact intake, pack, control and observations,
derives metrics independently and preserves this authenticity limitation for
human review. A successful comparison does not authorize installation, runtime
activation, registry mutation or promotion.

`technology_experiment_cases_v1.json` is the minimal declarative case-universe
shape. Its check identifiers are the same canonical identifiers required by the
pack contract; the actual pack still has to bind each case to an exact reviewed
intake, fixed control snapshot and paired preproduced observations. The dataset
contains no candidate source, command, module, package, path or URL.
