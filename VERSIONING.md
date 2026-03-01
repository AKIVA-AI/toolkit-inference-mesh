# Versioning policy (Toolkit Inference Mesh)

This tool follows SemVer with an additional constraint: the repo is an Toolkit-branded fork of `GradientHQ/parallax`.

## SemVer rules

- `PATCH`: bug fixes and docs; no breaking CLI changes.
- `MINOR`: additive flags/commands; additive fields in the Toolkit inference event log.
- `MAJOR`: breaking API/CLI changes, breaking schema changes, or large behavior shifts.

## Upstream-driven changes

Upstream Parallax changes can force larger version jumps.

Release notes should always include:

- upstream commit hash (see `UPSTREAM.md`)
- notable upstream features/fixes
- Toolkit-specific deltas

## Deprecations

Deprecated features are announced one minor version in advance and removed in the next major version.


