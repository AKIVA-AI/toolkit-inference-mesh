## Upstream

- Project: `GradientHQ/parallax`
- URL: https://github.com/GradientHQ/parallax
- Upstream commit vendored: `143a2853fb88ec59fc593909f8554f8ea1c18923`
- License: Apache-2.0 (`LICENSE`)

## Why this fork exists

- Brand + packaging: publish under Toolkit naming (`toolkit-inference-mesh`, `toolkit-mesh` CLI).
- Provide a stable base for Toolkit enhancements (enterprise governance, fleet controls, observability integrations).

## How to update from upstream (recommended workflow)

1. Pull latest upstream into `enterprise-tools/_parallax_upstream` (temporary clone).
2. Review upstream release notes and breaking changes.
3. Re-vendor the new upstream snapshot into `enterprise-tools/inference-mesh`.
4. Record the new upstream commit hash here and summarize Toolkit-specific deltas.


