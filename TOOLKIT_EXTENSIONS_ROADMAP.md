# Toolkit Inference Mesh: Toolkit Extensions Roadmap

`enterprise-tools/inference-mesh/` is an Toolkit-branded fork of Parallax (Apache-2.0) and serves as the OSS distributed
inference engine core.

This document defines the intended Toolkit extension surface (OSS add-ons and Pro modules) without forking the entire
runtime into an unmergeable codebase.

## Guiding principle

Keep upstream parity for the distributed engine. Add Toolkit value in *adjacent* modules:

- a gateway layer
- governance and fleet controls
- integrations (eval gates, provenance, cost/latency, policy enforcement)

## Near-term (OSS add-ons)

1. **Toolkit Gateway (OpenAI-compatible)**
   - Front Parallax scheduler with a stable OpenAI-compatible API + SSE
   - Request normalization, headers, timeouts, retries, circuit breakers
   - Structured request logs (JSON) suitable for downstream cost/latency analysis

2. **Telemetry schema**
   - Define a stable JSONL event schema for inference events:
     - model, latency, success, token estimates, node/worker id, request type, tier
   - Provide a CLI to export/convert logs to the schema
   - Align with `docs/enterprise-tools/schemas/toolkit_inference_event.schema.json`

3. **Release criteria hooks**
   - Define how Neural Forge/Eval Harness â€œpassâ€ criteria attach to a model deployment
   - Keep this as metadata and/or a sidecar policy file (no heavy registry required for OSS)

## Pro modules (commercial)

1. **Multi-tenant governance**
   - Projects/tenants, RBAC, and group mapping
   - Budget enforcement + per-tenant quotas

2. **Audit and policy enforcement**
   - Audit exports (SIEM sinks, object storage)
   - Policy gates (PII/compliance rules) at the gateway

3. **Fleet control plane**
   - Node enrollment + cert rotation + upgrades
   - Health scoring, autoscaling signals, and SLO monitoring

## Integration points across Toolkit tools

- `toolkit-mlsbom` signs:
  - suite packs (Eval Harness / Policy Test Bench)
  - finetune job bundles
  - deployment criteria metadata shipped with model releases
- `toolkit-opt` consumes:
  - gateway/mesh inference event logs to recommend routing and budget policies
- `toolkit-policy` and `toolkit-eval` produce:
  - signed packs + deterministic reports used as â€œpromotion gatesâ€

## Practical next steps

- Add a new folder alongside Parallax code for Toolkit modules, e.g. `toolkit_extensions/`, and keep the coupling via:
  - HTTP APIs
  - config files
  - documented interfaces


