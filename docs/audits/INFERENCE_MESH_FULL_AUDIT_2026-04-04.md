# Toolkit Inference Mesh — Full Audit Report

**Date:** 2026-04-04
**Auditor:** Claude Code (Opus 4.6)
**System:** toolkit-inference-mesh
**Archetype:** 9 — Developer Tool / CLI Utility
**Standards Baseline:** Akiva Build Standard v2.14, Archetypes v2.0
**Prior Audit:** 2026-03-09 (v2.13, 64.8/100 raw → 65/100 rounded)

> **Dimension Model Change:** The v2.14 Build Standard restructured dimensions from the
> v2.13 model. Key changes: D4 is now "API Surface Quality" (was "Domain Model Depth"),
> D10 is now "CI/CD" (was "Performance & Scalability"), D12 is now "Domain Capability"
> (was "CI/CD"), D13 is now "AI/ML Capability" (was "Error Handling"). Prior scores are
> mapped by content similarity, not dimension number. Composites are not directly comparable.

---

## Composite Score: 59.8 / 100

**Rating:** Pre-Production (below 60 minimum for Production Viable)
**Minimum Gaps:** 2 dimensions below minimum (D4, D7)
**Delta from prior:** -5.0 (structural — dimension model change, not system regression)
**CODEBASE_MAP.md:** Missing (Phase 0.5 gap)

---

## Score Summary

| Dim | Dimension | Weight | Score | Prior* | Min | Met? | Cap Condition | Fixable By |
|-----|-----------|--------|-------|--------|-----|------|---------------|------------|
| 1 | Architecture Integrity | 8% | 7 | 7 | — | — | No CODEBASE_MAP prevents 8 | Agent |
| 2 | Auth & Authorization | 2% | 3 | 3 | — | — | No auth layer; deferred to deployment | Accepted |
| 3 | Data Isolation & RLS | 0% | 2 | 2 | — | — | N/A for CLI tool | N/A |
| 4 | **API Surface Quality** | **12%** | **6** | N/A | **7** | **NO** | No health endpoints, no rate limiting, CORS open, no API docs | Agent |
| 5 | Data Layer Integrity | 2% | 4 | 4 | — | — | File I/O only, no retention policy | Agent |
| 6 | Frontend Quality | 0% | 3 | 3 | — | — | Upstream pre-built bundle | N/A |
| 7 | **Testing & QA** | **15%** | **6** | 6 | **7** | **NO** | Coverage threshold 3% (req 60%), mypy non-blocking, no E2E | Agent |
| 8 | Security Posture | 10% | 6 | 6 | 6 | Yes | No SBOM (-1), CORS open, security scans non-blocking | Agent |
| 9 | Observability & Monitoring | 5% | 5 | 5 | — | — | No metrics endpoint, no health checks, no tracing | Agent |
| 10 | CI/CD | 10% | 7 | 7† | 6 | Yes | mypy non-blocking, coverage threshold 3% | Agent |
| 11 | Documentation Accuracy | 10% | 6 | 6 | 6 | Yes | No API reference, no CODEBASE_MAP, no issue/PR templates | Agent |
| 12 | Domain Capability Depth | 8% | 8 | 8† | 6 | Yes | No quantization management, limited sampling | — |
| 13 | AI/ML Capability | 5% | 6 | 6† | — | — | No confidence matrix, no circuit breaker, no eval set | Agent |
| 14 | Connectivity & Channel | 2% | 6 | 6† | — | — | No MCP server, no webhooks | Agent |
| 15 | Agentic UI/UX | 0% | 1 | N/A | — | — | N/A for CLI tool | N/A |
| 16 | UX Quality | 0% | 2 | N/A | — | — | N/A for CLI tool | N/A |
| 17 | User Journey | 0% | 1 | N/A | — | — | N/A for CLI tool | N/A |
| 18 | Zero Trust Architecture | 2% | 3 | N/A | — | — | No service-to-service auth, P2P implicit trust | Human |
| 19 | Enterprise Security | 5% | 5 | 8† | — | — | No SBOM, no pen test, no formal vuln mgmt | Agent+Human |
| 20 | Operational Readiness | 2% | 5 | 7† | — | — | No runbook, no SLOs, no health endpoints | Agent |
| 21 | Agentic Workspace | 2% | 2 | 2 | — | — | Not an agentic tool | N/A |

\* Prior scores mapped by content similarity across dimension model versions.
† Prior dimension number differs; mapped by content (e.g., prior D12 "CI/CD" → current D10).

### Composite Calculation

```
Σ(Weight × Score) = 0.56 + 0.06 + 0.00 + 0.72 + 0.08 + 0.00 + 0.90 + 0.60
                  + 0.25 + 0.70 + 0.60 + 0.64 + 0.30 + 0.12 + 0.00 + 0.00
                  + 0.00 + 0.06 + 0.25 + 0.10 + 0.04
                  = 5.98

Composite = 5.98 / 10 × 100 = 59.8/100
```

---

## Dimension Details

### Dim 1: Architecture Integrity — 7/10 (8%)

**Evidence:**
- Clean separation: `src/parallax/` (core engine), `src/scheduling/` (distributed allocation/routing), `src/backend/` (HTTP scheduler), `src/parallax_utils/` (utilities)
- Factory pattern for executors (`factory.py`: MLX, SGLang, vLLM)
- Strategy pattern for layer allocation (`GreedyLayerAllocator`, `DynamicProgrammingLayerAllocator`) with shared `BaseLayerAllocator`
- Strategy pattern for request routing (`RoundRobinPipelineRouting`, `DynamicProgrammingRouting`) with ABC interface
- State machine for request lifecycle (`RequestStatus` enum: PREFILLING → DECODING → FINISHED_*)
- P2P layer with protobuf serialization (`src/parallax/p2p/`)
- Control-plane contracts (`src/parallax/control_plane/contracts.py`) with optional framework imports and inline fallbacks
- **22K LOC source** — verified custom implementation, not scaffolding

**Caps:** No `docs/CODEBASE_MAP.md` (Phase 0.5 requirement) prevents 8+.

### Dim 2: Auth & Authorization — 3/10 (2%)

**Evidence:**
- No authentication on HTTP endpoints
- CORS `allow_origins=["*"]` in `src/backend/main.py:35`
- `.env.example` has `API_KEY` placeholder but no implementation
- No JWT, OAuth, or API key middleware
- SECURITY.md explicitly defers auth to deployment infrastructure

**Accepted:** Auth deferral is appropriate for Archetype 9 CLI tool (weight = 2%).

### Dim 3: Data Isolation & RLS — 2/10 (0%)

**Evidence:**
- `InferenceEvent` Pydantic model has `tenant` and `project` fields
- No enforcement of tenant isolation anywhere in scheduler, executor, or cache layers
- Multi-tenancy is not a design goal (weight = 0%)

### Dim 4: API Surface Quality — 6/10 (12%, **min 7 — NOT MET**)

**Evidence (+):**
- CLI entry point `toolkit-mesh` with clean argparse subcommands (run/join/chat) — `src/parallax/cli.py:445 LOC`
- OpenAI-compatible `/v1/chat/completions` endpoint with SSE streaming
- Pydantic schema validation on all request/response models
- Comprehensive `.env.example` (170 lines, 100+ documented variables)
- Typed error responses via `HTTPStatus`
- Graceful shutdown with SIGINT → SIGTERM → SIGKILL escalation

**Evidence (-):**
- No `/health` or `/ready` endpoints
- No rate limiting (mentioned in `.env.example`, absent from code)
- CORS `allow_origins=["*"]`
- No published API docs or OpenAPI spec
- No JSON output mode for CLI operations (event log only)

**Rubric:** 5-6 = "Validated inputs; consistent errors; basic health checks"; 7-8 requires rate limiting + CORS hardened + documentation. Score 6 (strong validation compensates for missing health checks; cannot reach 7 without rate limiting and docs).

**Required Capabilities Gap:** Archetype 9 requires JSON output mode for CI integration — partially met (JSONL event log, not CLI output).

### Dim 5: Data Layer Integrity — 4/10 (2%)

**Evidence:**
- JSONL event logging with thread-safe writes (`_event_log_lock`)
- Path traversal prevention with whitelist validation
- KV cache has explicit allocation/deallocation lifecycle
- Model weights managed through HuggingFace Hub + selective download
- No log rotation or retention policy
- No backup/recovery
- No data migration strategy for event schema changes

### Dim 6: Frontend Quality — 3/10 (0%)

**Evidence:**
- Pre-built React+TypeScript frontend in `src/frontend/dist/`
- Chat interface and node configuration UI (upstream)
- Not auditable or customizable; not the primary interface

### Dim 7: Testing & QA — 6/10 (15%, **min 7 — NOT MET**)

**Evidence (+):**
- **30 test files, ~150+ tests, 6,148 LOC** (28% test-to-source ratio)
- CI matrix: ubuntu + macOS × Python 3.11/3.12/3.13 (5 configurations)
- Good coverage: scheduler (4 files, ~1,100 LOC), event logging (25 tests), routing edge cases, cache management, executors
- `conftest.py` (809 LOC) with graceful hardware mocking (skips when MLX/ZMQ unavailable)
- Ruff + Black enforced (blocking) in CI
- Codecov upload configured

**Evidence (-):**
- **Coverage threshold: `--cov-fail-under=3`** — Archetype 9 requires 60%+ minimum
- **mypy: `continue-on-error: true`** — type checking not enforced (required capability)
- No E2E integration tests (full scheduler→node→executor pipeline)
- `test_prefix_cache.py` is only 32 lines (stubby)
- No mutation testing
- `fail_ci_if_error: false` for Codecov — coverage regressions not caught

**Rubric:** 5-6 = "Tests pass in CI; basic coverage on critical paths"; 7 requires "Comprehensive test suite; E2E on critical journeys; CI enforced". Cannot reach 7 without enforcing coverage threshold and type checking.

**Prior gap unchanged:** D7 minimum was not met in the 2026-03-09 audit either.

### Dim 8: Security Posture — 6/10 (10%, min 6 — MET)

**Evidence (+):**
- SECURITY.md with responsible disclosure, deployment hardening notes, supported versions
- Path traversal vulnerability FIXED (whitelist validation in `toolkit_event_log.py`)
- Pydantic schema validation on all event models
- No `eval()`, `exec()`, or `shell=True` in source
- Secrets externalized (env vars, `.env.example`)
- Dependabot configured (pip + github-actions, weekly) — `.github/dependabot.yml`
- Bandit scanning with justified skip list in `pyproject.toml`
- Pre-commit hooks (ruff, isort, black, autoflake, trailing-whitespace)
- Input validation on CLI args (`cli.py`)

**Evidence (-):**
- CORS `allow_origins=["*"]` in `src/backend/main.py:35`
- Security scans (bandit, safety) `continue-on-error: true` — non-blocking
- No SBOM generation (Repository Controls §8: -1 for Dim 8)
- Telemetry `upload_package_info()` to `chatbe-dev.gradient.network` without explicit opt-in
- No rate limiting
- No TLS (deferred to deployment — acceptable for CLI tool)

**Repository Controls impact:** +0 for SECURITY.md, +0 for Dependabot, -1 for no SBOM.
**Net:** Clean code practices (7) - SBOM gap (-1) = 6. CORS and non-blocking scans prevent 7 even without SBOM penalty.

### Dim 9: Observability & Monitoring — 5/10 (5%)

**Evidence (+):**
- Custom structured logging with colored output, package-level filtering (`logging_config.py:140 LOC`)
- JSONL inference event logging with Pydantic schema (`toolkit_event_log.py:169 LOC`)
- Cost tracking per inference call (`estimate_cost_usd()`)
- Request metrics extraction (TPS, TTFT) via `request_metrics.py`
- `SharedState` for runtime metrics

**Evidence (-):**
- No Prometheus/metrics endpoint (mentioned in `.env.example`, not implemented)
- No distributed tracing (OpenTelemetry/Jaeger)
- No `/health` or `/ready` endpoints
- No log rotation for JSONL event logs
- No monitoring dashboard, no alerting, no SLOs
- AI Resilience Gate R-3 (friction telemetry): absent

**Standards caps:** AI Resilience Standard caps D9 at 7 without friction telemetry; Operational Standard caps at 7 without monitoring dashboard. Both are above current score.

### Dim 10: CI/CD — 7/10 (10%, min 6 — MET)

**Evidence (+):**
- 5 GitHub Actions workflows (ci, build-images, build-spark-image, pre-commit, commit-check)
- Matrix testing: ubuntu + macOS × Python 3.11/3.12/3.13
- Docker build + smoke test (`docker run toolkit-mesh --help`)
- Ruff linting and Black formatting enforced (blocking)
- Codecov upload
- Dependabot configured for pip + github-actions
- Pre-commit hooks in CI
- Pip caching in CI

**Evidence (-):**
- mypy `continue-on-error: true` — type checking not blocking
- Bandit/safety `continue-on-error: true` — security scans not blocking
- Coverage threshold: `--cov-fail-under=3` (meaningless)
- `fail_ci_if_error: false` for Codecov
- Docker image `build-images.yaml` references upstream namespace `gradientservice/parallax`
- No release automation (no tag-based publishing)
- No SBOM in CI pipeline
- No coverage artifact publishing (beyond Codecov)

**Repository Controls impact:** -1 for single-version-only CI? No — matrix testing covers 5 configs. -1 for coverage not tracked in CI? No — Codecov exists. Branch protection: not verified in code.

**Rubric:** Solid matrix testing + Docker CI + Dependabot pushes above 6; non-blocking mypy/security prevents 8.

### Dim 11: Documentation Accuracy — 6/10 (10%, min 6 — MET)

**Evidence (+):**
- `README.md` (71 lines): overview, supported models, quick reference
- `docs/user_guide/install.md` + `quick_start.md`: step-by-step with FAQ
- `src/scheduling/README.md` (162 lines): excellent architecture documentation
- `TOOLKIT_ENHANCEMENTS.md` (447 lines): detailed enhancement audit
- `CONTRIBUTING.md` (16 lines): basic workflow
- `CHANGELOG.md`, `VERSIONING.md`, `RELEASING.md`, `UPSTREAM.md`
- `SECURITY.md` with deployment hardening guidance
- CLI `--help` output comprehensive

**Evidence (-):**
- No API reference for `/v1/chat/completions` or scheduler management endpoints
- No `docs/CODEBASE_MAP.md` (Phase 0.5 requirement)
- No `.github/ISSUE_TEMPLATE/` or `.github/PULL_REQUEST_TEMPLATE.md` (required for Archetype 9 per Repository Controls §1.3)
- Docstrings inconsistent (scheduling/allocation excellent; http_server/shard_loader minimal)
- No documentation build validation in CI

**Repository Controls impact:** Dim 11 capped at 7 without docs build validation (not limiting at score 6).

### Dim 12: Domain Capability Depth — 8/10 (8%, min 6 — MET)

**Evidence:**
- **Pipeline-parallel inference** across SGLang, vLLM, MLX backends
- **12 model implementations**: DeepSeek V2/V3/V3.2, Qwen 2/3/3-MoE/3-Next, Llama, MiniMax, GLM-4, gpt-oss
- **Continuous batching scheduler** with 2-phase admission + batching (`scheduler.py:330 LOC`)
- **Layer allocation**: DP optimization (joint concurrency×latency scoring `k²/s*(k)`) and Greedy strategies with water-filling rebalance
- **Request routing**: DP warm-up with turning point detection + shard-level Dijkstra routing
- **P2P networking** via Lattica/libp2p with 6 bootstrap + 6 relay servers
- **KV cache management**: Paged attention, linear cache, DSA cache, prefix caching (radix tree)
- **Dynamic node join/leave** with automatic re-sharding
- **Cross-device pipeline**: CUDA ↔ MLX with protobuf serialization
- **Selective weight downloading** from HuggingFace Hub

**22K LOC of verified custom implementation — not scaffolding.**

**Caps:** No quantization management in-code (deferred to backends), limited sampling strategies prevent 9.

### Dim 13: AI/ML Capability — 6/10 (5%)

**Evidence (+):**
- Multi-backend inference (SGLang, vLLM, MLX) with executor factory
- Streaming SSE support for real-time token delivery
- Cost tracking per inference call via `estimate_cost_usd()`
- Token counting (input + output)
- Control-plane contracts with optional akiva-execution-contracts integration
- Multiple model architectures supported (12 families)

**Evidence (-):**
- No confidence threshold matrix (AI Resilience R-1) — caps D13 at 7
- No model registry with tier naming (LLM Gateway Standard) — caps D13 at 6
- No circuit breaker pattern for backend failures
- No fallback chain between inference backends
- No trust metadata in responses (AI Service Standard)
- No degradation simulation testing (AI Resilience R-2)
- No eval set or prompt regression tests
- No feedback loop (AI Resilience R-5)

**Standards caps:** LLM Gateway caps at 6 without model registry. AI Resilience caps at 7 without confidence matrix. Current score is at the LLM Gateway cap.

### Dim 14: Connectivity & Channel — 6/10 (2%)

**Evidence:**
- P2P networking via Lattica/libp2p (sophisticated NAT traversal)
- ZMQ IPC for executor↔HTTP server communication
- gRPC/Protobuf for inter-peer hidden state forwarding
- OpenAI-compatible HTTP API (`/v1/chat/completions`)
- HuggingFace Hub integration for model downloads
- No MCP server, no webhook support, no tool registry

### Dim 15: Agentic UI/UX — 1/10 (0%)

Not applicable for CLI tool. Weight = 0%.

### Dim 16: UX Quality — 2/10 (0%)

Pre-built upstream React UI exists but is not the primary interface. Weight = 0%.

### Dim 17: User Journey — 1/10 (0%)

Not applicable. Weight = 0%.

### Dim 18: Zero Trust Architecture — 3/10 (2%)

**Evidence:**
- Secrets externalized via env vars (not hardcoded)
- No shared credentials in code
- No service-to-service auth (P2P nodes trust each other implicitly)
- No mTLS between peers or HTTP servers
- No network segmentation beyond deployment guidance in SECURITY.md

### Dim 19: Enterprise Security & Compliance — 5/10 (5%)

**Evidence (+):**
- Apache 2.0 license with upstream attribution (UPSTREAM.md, NOTICE)
- SECURITY.md with responsible disclosure process
- Dependabot for automated dependency updates
- Bandit security scanning + Safety dependency checks
- Pre-commit hooks
- Justified Bandit skip list in `pyproject.toml`

**Evidence (-):**
- No SBOM generation (CycloneDX/SPDX)
- No penetration testing
- No formal vulnerability management process
- No key management service (KMS/Vault)
- No license compliance check in CI (required for Archetype 9 per Repository Controls §5.4)

**Certification gaps:** SBOM/SLSA Level 2 required for Archetype 9 (not met). NIST SSDF recommended (not met).

### Dim 20: Operational Readiness — 5/10 (2%)

**Evidence (+):**
- Docker support with Dockerfile + Dockerfile.spark
- Docker smoke test in CI
- Graceful shutdown with signal escalation (SIGINT→SIGTERM→SIGKILL)
- `.env.example` with comprehensive deployment configuration
- `RELEASING.md` with release process documentation
- `VERSIONING.md` with SemVer policy
- Benchmark tooling included (`src/backend/benchmark/`)

**Evidence (-):**
- No deployment procedure documentation
- No runbook
- No health check endpoints
- No SLOs defined
- No monitoring dashboard
- No incident response procedure
- No production readiness review

**Archetype 9 context:** "Operational Readiness" at 2% weight is scoped to "Docker support, install reliability" per archetype description. Docker and graceful shutdown are solid for a CLI tool.

### Dim 21: Agentic Workspace — 2/10 (2%)

Not an agentic tool. Provides OpenAI-compatible API consumed by agents but exhibits no agent behavior itself. Appropriate for Archetype 9.

### Dims 22-24: Healthcare & Federal

Not scored for Archetype 9. Weight = 0%.

---

## Archetype Minimum Compliance

| Dimension | Minimum | Actual | Status | Gap |
|-----------|---------|--------|--------|-----|
| D4: API Surface Quality | 7 | 6 | **FAIL** | +1 needed |
| D7: Testing & QA | 7 | 6 | **FAIL** | +1 needed |
| D8: Security Posture | 6 | 6 | PASS | — |
| D10: CI/CD | 6 | 7 | PASS | — |
| D11: Documentation | 6 | 6 | PASS | — |
| D12: Domain Capability | 6 | 8 | PASS | — |
| Composite | 60 | 59.8 | **FAIL** | +0.2 needed |

**3 minimums not met:** D4, D7, composite.

---

## Required Capabilities Check (Archetype 9)

| Requirement | Status | Evidence |
|-------------|--------|----------|
| CLI entry point | PASS | `toolkit-mesh` via `pyproject.toml` entry point |
| JSON output mode for CI | PARTIAL | JSONL event log exists; no JSON mode for CLI operations |
| Zero-dependency core | PARTIAL | 32 runtime deps; optional extras for ML backends |
| Coverage threshold 60%+ in CI | **FAIL** | `--cov-fail-under=3` |
| Linting in CI | PASS | ruff + black enforced (blocking) |
| Type checking in CI | **FAIL** | mypy `continue-on-error: true` (non-blocking) |
| Docker support | PASS | Dockerfile + smoke test in CI |
| README with install/usage/examples | PASS | README + user_guide/ |
| Semantic versioning | PASS | v0.1.2, VERSIONING.md |
| Publishable to PyPI | PASS | pyproject.toml with entry points and metadata |

---

## Standards Compliance Matrix

### Core Standards

| Standard | Version | Applicable | Key Findings |
|----------|---------|------------|-------------|
| Build Standard | v2.14 | Yes | Dimension model applied; scoring rubric followed |
| Archetypes | v2.0 | Yes | Archetype 9 weights and minimums applied |
| Sprint Protocol | v3.4 | Yes | SA-1 through SA-13 not applicable (no sprint in scope) |
| Repository Controls | v1.3 | Yes | Dependabot ✓, SECURITY.md ✓, no SBOM ✗, no issue/PR templates ✗ |
| Operational Standard | v1.4 | Partial | CLI tool; Docker and graceful shutdown sufficient |
| Pre-Push | v1.2 | Yes | ruff + black enforced; mypy not enforced |

### AI Standards

| Standard | Version | Applicable | Key Findings |
|----------|---------|------------|-------------|
| AI Service Standard | v1.5 | Yes | No AI surface inventory, no trust metadata in responses |
| AI Agent Runtime | v1.8 | Yes | Control-plane contracts present (optional framework imports); no runtime tier classification |
| AI Resilience | v1.3 | Yes | R-1 (confidence matrix) absent → D13 cap 7; R-2 (degradation testing) absent → D13 cap 7; R-3 (friction telemetry) absent → D9 cap 7 |
| LLM Gateway | v1.2 | Yes | No model registry → D13 cap 6; no circuit breaker; no fallback chains; no per-tenant budgets |
| Streaming AI Rendering | v1.0 | Yes | SSE streaming present; no text stability tiers implemented; no TTFR measurement |
| BENCHMARK | v1.5 | No | No self-improvement or continuous monitoring |
| Knowledge Representation | v1.0 | No | Not a domain-specific inference tool |

### Domain-Specific Standards

| Standard | Version | Applicable | Key Findings |
|----------|---------|------------|-------------|
| Integration & Webhook | v1.1 | Yes | No MCP server; no webhook support; HTTP API present |
| User Trust | v1.4 | Partial | T-1 (state transparency) not met — routing decisions not legible to consumers |
| Data Isolation | v1.1 | No | Not multi-tenant (weight = 0%) |
| Compliance Framework | v1.0 | Partial | No SBOM, no SLSA alignment |
| SBOM & Supply Chain | v1.0 | Yes | **Not implemented** — required for Archetype 9 |
| AI Governance & Ethics | v1.0 | No | Not high-risk AI per EU AI Act |
| Change Management | v1.0 | No | No change control board needed for CLI tool |

---

## Top 5 Gaps (Ranked by Score Impact)

### 1. D7: Coverage threshold and type checking not enforced (Impact: -1.5/100)

**Current:** `--cov-fail-under=3`, mypy `continue-on-error: true`
**Required:** Coverage ≥60%, mypy blocking
**Fix:** Raise `--cov-fail-under` to 60, remove `continue-on-error: true` from mypy step, fix type errors.
**Fixable by:** Agent
**Files:** `.github/workflows/ci.yml:50,57`

### 2. D4: No health endpoints, no API docs, CORS open (Impact: -1.2/100)

**Current:** No `/health` or `/ready`, CORS `allow_origins=["*"]`, no OpenAPI spec
**Required:** Health probes, CORS hardened, API documentation
**Fix:** Add `/health` and `/ready` endpoints to `src/backend/main.py` and `src/parallax/server/http_server.py`. Replace CORS wildcard with env-configurable allowlist. Generate OpenAPI spec from FastAPI.
**Fixable by:** Agent
**Files:** `src/backend/main.py`, `src/parallax/server/http_server.py`

### 3. D8: No SBOM generation (Impact: -1.0/100)

**Current:** No CycloneDX/SPDX generation in CI
**Required:** SBOM on every release build (Repository Controls §8, Archetype 9 certification)
**Fix:** Add Syft SBOM generation step to CI, Grype vulnerability scan.
**Fixable by:** Agent
**Files:** `.github/workflows/ci.yml`

### 4. D11: No API reference, no CODEBASE_MAP, no issue/PR templates (Impact: -1.0/100)

**Current:** User guides exist but no API docs, no CODEBASE_MAP, no GitHub templates
**Required:** API reference, CODEBASE_MAP (Phase 0.5), issue/PR templates (Repository Controls §1.3)
**Fix:** Generate API docs from FastAPI OpenAPI spec. Create `docs/CODEBASE_MAP.md`. Add `.github/ISSUE_TEMPLATE/` and `.github/PULL_REQUEST_TEMPLATE.md`.
**Fixable by:** Agent
**Files:** `docs/`, `.github/`

### 5. D9: No metrics endpoint, no health checks (Impact: -0.5/100)

**Current:** Structured logging only; no Prometheus, no health checks, no tracing
**Required:** Structured metrics export, health endpoint
**Fix:** Add Prometheus metrics endpoint (request count, latency histogram, cache hit rate). Add `/health` endpoint. Add OpenTelemetry trace context propagation.
**Fixable by:** Agent
**Files:** `src/backend/main.py`, `src/parallax/server/http_server.py`

---

## Path to 60 (Production Viable)

Close D4 and D7 minimums. Both are agent-fixable.

| Task | Dimension | Impact | Priority |
|------|-----------|--------|----------|
| Raise `--cov-fail-under` to 60 in CI | D7: 6→7 | +1.5/100 | P0 |
| Enforce mypy (remove `continue-on-error`) | D7: 6→7 | (included) | P0 |
| Add `/health` + `/ready` endpoints | D4: 6→7 | +1.2/100 | P0 |
| Replace CORS wildcard with configurable allowlist | D4: 6→7 | (included) | P0 |
| Add OpenAPI spec / API docs | D4: 6→7 | (included) | P0 |

**Projected composite after Sprint 0:** 59.8 + 1.5 + 1.2 = **62.5/100**

---

## Path to 65

| Task | Dimension | Impact | Priority |
|------|-----------|--------|----------|
| All Sprint 0 tasks above | D4/D7 | +2.7 | P0 |
| Add SBOM generation (Syft + Grype) to CI | D8: 6→7 | +1.0/100 | P1 |
| Enforce security scans (remove `continue-on-error`) | D8: 6→7 | (included) | P1 |
| Add CODEBASE_MAP.md | D11: 6→7 | +1.0/100 | P1 |
| Add issue/PR templates | D11: 6→7 | (included) | P1 |
| Add API reference documentation | D11: 6→7 | (included) | P1 |
| Add `/health` + Prometheus metrics endpoint | D9: 5→6 | +0.5/100 | P1 |

**Projected composite:** 59.8 + 2.7 + 1.0 + 1.0 + 0.5 = **65.0/100**

All gaps to 65 are **agent-fixable**. No human-only blockers.

---

## Path to 70

Beyond the 65 path, reaching 70 requires:

| Task | Dimension | Impact | Fixable By |
|------|-----------|--------|------------|
| Create model registry with tier naming | D13: 6→7 | +0.5/100 | Agent |
| Add circuit breaker for inference backends | D13: 6→7 | (included) | Agent |
| Add confidence threshold matrix doc | D13: 6→7 | (included) | Agent |
| Create CODEBASE_MAP + architectural ADR | D1: 7→8 | +0.8/100 | Agent |
| Add SBOM/SLSA Level 2, license audit in CI | D19: 5→6 | +0.5/100 | Agent |
| E2E integration tests in CI | D7: 7→8 | +1.5/100 | Agent+Human (needs GPU) |
| Release automation (tag → build → publish) | D10: 7→8 | +1.0/100 | Agent |

**Projected:** 65.0 + 0.5 + 0.8 + 0.5 + 1.5 + 1.0 = **69.3/100**

**Human-only blockers for 70+:**
- E2E integration tests require GPU hardware in CI
- Penetration testing (D19→7)
- mTLS/service-to-service auth for P2P layer (D18→5)

---

## Human-Only Blockers

| Item | Dimension Impact | Why Human |
|------|-----------------|-----------|
| GPU CI runners for E2E tests | D7 capped at 7 without hardware tests | Infrastructure procurement |
| Penetration testing | D19 capped at 6 without pen test | External vendor engagement |
| mTLS for P2P layer | D18 capped at 3 without service auth | Architecture decision + cert infrastructure |
| Domain expert review of model implementations | D12 capped at 8 without expert validation | External expertise |
| Production deployment + monitoring | D20 capped at 5 without production evidence | Deployment infrastructure |

---

## Functional Tests

**Not required** for standard Archetype 9 CLI tools. FT-1 through FT-9 apply only to orchestrator-type tools (e.g., agentic-rag-tuning-orchestrator). toolkit-inference-mesh is an inference engine, not an orchestrator.

---

## Accepted Exceptions

| Item | Reason |
|------|--------|
| No auth in HTTP server | Archetype 9; SECURITY.md documents deployer responsibility |
| No multi-tenancy | Not a design goal (weight = 0%) |
| No frontend quality gate | Upstream pre-built bundle (weight = 0%) |
| No agentic capabilities | Inference engine, not agent (weight = 0-2%) |
| Upstream telemetry (`upload_package_info`) | Inherited from fork; `--skip-upload` flag available |
| No TLS in HTTP servers | Deployment responsibility per SECURITY.md |

---

## Audit Methodology

- Read all Python source (22K LOC across ~130 files)
- Read all test files (6,148 LOC across 30 files)
- Read all CI/CD workflows (5 GitHub Actions files)
- Read all documentation (README, user guides, security, contributing, versioning, releasing, changelog)
- Read Docker configuration (Dockerfile, Dockerfile.spark)
- Read pyproject.toml for dependency and packaging analysis
- Read control-plane contracts
- Verified SECURITY.md, CONTRIBUTING.md, Dependabot configuration
- Confirmed absence of issue/PR templates, CODEBASE_MAP, SBOM
- Grepped for security anti-patterns (eval, exec, shell=True, hardcoded secrets, CORS, continue-on-error)
- Verified coverage threshold (3%) and mypy enforcement (non-blocking)
- Evaluated against all applicable standards (6 core, 7 AI, 7 domain-specific)
- Applied Archetype 9 weights and minimums from SYSTEM_ARCHETYPES.md v2.0
- Mapped prior audit scores by content across dimension model change

---

_Audit produced under Akiva Build Standard v2.14, Archetypes v2.0._
_Prior audit: `docs/audits/TOOLKIT_INFERENCE_MESH_AUDIT_REPORT_2026-03-09.md` (v2.13, 64.8/100)._
