# Toolkit Inference Mesh System Audit Report

**Date:** 2026-03-09
**Auditor:** Claude Code (Opus 4.6)
**System:** toolkit-inference-mesh
**Archetype:** 9 -- Developer Tool / CLI
**Previous Audit:** None (initial audit)

## Composite Score: 62.2 / 100

### Score Summary Table

| Dim | Dimension Name | Weight | Score | Weighted | Minimum | Met? |
|-----|----------------|--------|-------|----------|---------|------|
| 1 | Architecture & Design | 8% | 7 | 0.56 | -- | -- |
| 2 | Auth & Identity | 2% | 3 | 0.06 | -- | -- |
| 3 | Multi-Tenancy | 0% | 2 | 0.00 | -- | -- |
| 4 | Domain Model Depth | 12% | 8 | 0.96 | 7 | Yes |
| 5 | Connectivity & Integration | 2% | 6 | 0.12 | -- | -- |
| 6 | Billing & Monetization | 0% | 0 | 0.00 | -- | -- |
| 7 | Testing & QA | 15% | 6 | 0.90 | 7 | **NO** |
| 8 | Security & Hardening | 10% | 6 | 0.60 | 6 | Yes |
| 9 | Observability & Monitoring | 5% | 5 | 0.25 | -- | -- |
| 10 | Performance & Scalability | 10% | 8 | 0.80 | 6 | Yes |
| 11 | Documentation & DX | 10% | 6 | 0.60 | 6 | Yes |
| 12 | CI/CD & DevOps | 8% | 7 | 0.56 | 6 | Yes |
| 13 | Error Handling & Resilience | 5% | 6 | 0.30 | -- | -- |
| 14 | Data Management | 2% | 4 | 0.08 | -- | -- |
| 15 | UI/UX | 0% | 3 | 0.00 | -- | -- |
| 16 | Internationalization | 0% | 0 | 0.00 | -- | -- |
| 17 | Accessibility | 0% | 0 | 0.00 | -- | -- |
| 18 | Compliance & Licensing | 2% | 8 | 0.16 | -- | -- |
| 19 | Extensibility & Plugin Arch | 5% | 7 | 0.35 | -- | -- |
| 20 | Deployment & Packaging | 2% | 7 | 0.14 | -- | -- |
| 21 | Agentic / Workspace | 2% | 2 | 0.04 | -- | -- |
| **TOTAL** | | **100%** | | **6.48** | | |

**Composite Score: 64.8 (raw weighted sum) -- rounded to 65/100**

**Archetype Minimum Gaps:** Dim 7 (Testing) scores 6, minimum is 7. One minimum not met.

---

## Dimension Details

### Dim 1: Architecture & Design -- Score: 7/10

**Findings:**
- Clean separation: `src/parallax/` (core engine), `src/backend/` (HTTP scheduler), `src/scheduling/` (allocation/routing), `src/parallax_utils/` (utilities)
- Well-defined executor pattern with factory (`factory.py`) supporting MLX, SGLang, and vLLM backends
- P2P layer using Lattica with protobuf message serialization
- Scheduler uses a 2-phase approach (admission + batching) with clean abstraction
- Layer allocation has two strategies (Greedy, DP) with a shared base class and water-filling rebalance
- Request routing has abstract base class with DP and round-robin implementations
- CLI is clean argparse with `run`, `join`, `chat` subcommands
- **Gap:** No formal interface contracts (e.g., Python Protocols or ABCs for executors). The executor base class exists but coupling between scheduler/executor could be tighter via explicit interfaces.

### Dim 2: Auth & Identity -- Score: 3/10

**Findings:**
- No authentication on HTTP endpoints. CORS is `allow_origins=["*"]` in `main.py`
- SECURITY.md acknowledges this: "Authn/Authz in front of exposed HTTP endpoints"
- `.env.example` has `API_KEY` placeholder but no implementation in code
- No JWT, OAuth, or API key middleware exists in the HTTP server
- **Gap:** Authentication is explicitly deferred to deployment infrastructure. Acceptable for a developer tool, but the scaffolding is absent.

### Dim 3: Multi-Tenancy -- Score: 2/10

**Findings:**
- Event logging captures `tenant` and `project` fields from headers (`x-tenant`, `x-project`)
- No tenant isolation in the scheduler, executor, or KV cache layers
- No per-tenant rate limiting or resource quotas
- Multi-tenancy is not a design goal for this tool (weight = 0%)

### Dim 4: Domain Model Depth -- Score: 8/10

**Findings:**
- **Pipeline parallel inference** is the core domain and is deeply modeled:
  - Layer allocation via DP and greedy strategies with water-filling rebalancing
  - Dynamic node join/leave with automatic re-sharding and warm-up truncation
  - KV cache management: paged attention, linear cache, DSA cache, prefix caching, radix cache
  - Request lifecycle: InitialRequest -> prefill -> decode with status machine (WAITING/PREFILL/DECODING/FINISHED_EOS/FINISHED_MAX_LENGTH)
  - Continuous batching scheduler with admission control and micro-batching
- Multi-model support: DeepSeek V2/V3, Qwen2/3, Llama, MiniMax, GLM-4, gpt-oss
- Cross-device pipeline: CUDA <-> MLX with protobuf serialization between peers
- Shard downloading with selective weight filtering
- **Strong domain implementation.** Deducted for: no model quantization management in-code (deferred to backends), limited sampling strategies.

### Dim 5: Connectivity & Integration -- Score: 6/10

**Findings:**
- P2P networking via Lattica (libp2p-based) with relay server support
- ZMQ IPC between HTTP server and executor processes
- OpenAI-compatible `/v1/chat/completions` endpoint (streaming + non-streaming)
- gRPC/protobuf for inter-peer forward messages
- HuggingFace Hub integration for model downloads
- **Gap:** No webhook/callback support, no plugin system for external integrations, no metrics export endpoint (Prometheus endpoint mentioned in .env but not implemented in code).

### Dim 6: Billing & Monetization -- Score: 0/10

**Findings:**
- Not applicable for this archetype (weight = 0%)
- Cost estimation exists in toolkit_event_log.py but is a telemetry feature, not billing

### Dim 7: Testing & QA -- Score: 6/10

**Findings:**
- 17 test files, ~3,242 lines of test code across ~24,816 LOC source = ~13% test-to-source ratio
- Scheduler tests are comprehensive: layer allocation, request routing, scheduler lifecycle (4 files, ~1,022 lines)
- Toolkit enhancement tests are thorough: 25 tests for event logging (421 lines)
- Executor pipeline tests verify cross-device inference correctness
- HTTP handler, message util, sampler, server args, shard loader all have unit tests
- `conftest.py` gracefully skips tests when hardware dependencies (mlx, zmq) are missing
- **Gaps:**
  - `mypy` in CI has `continue-on-error: true` and `|| true` -- type checking is not enforced
  - No coverage threshold enforced (codecov uploads but no gate)
  - No integration tests for the full scheduler -> node -> executor pipeline in CI
  - `test_prefix_cache.py` is only 32 lines (stubby)
  - Missing tests for: radix cache, cache_manager, shared_state, several model implementations
- **Minimum 7 required -- this is 6. Gap must be closed.**

### Dim 8: Security & Hardening -- Score: 6/10

**Findings:**
- Path traversal prevention in event log path validation (whitelist approach)
- Pydantic schema validation on all logged events
- Input validation on CLI args (validate_args)
- Bandit security scanning in CI (with reasonable skip list)
- Safety dependency checking in CI
- SECURITY.md with responsible disclosure guidance
- No `eval()`, `exec()`, or `shell=True` in Python source (mx.eval/model.eval are framework calls, not Python eval)
- **Gaps:**
  - CORS `allow_origins=["*"]` in production code
  - No rate limiting implemented (mentioned in .env but absent from code)
  - Bandit and safety scans use `continue-on-error: true` -- not blocking
  - `upload_package_info()` sends telemetry to `chatbe-dev.gradient.network` without explicit user consent (upstream behavior)
  - No TLS configuration in the HTTP servers
  - Dependabot not configured (no `.github/dependabot.yml`)

### Dim 9: Observability & Monitoring -- Score: 5/10

**Findings:**
- Custom logging framework with colored output, package-level filtering, configurable levels
- JSONL inference event logging with schema validation (Toolkit addition)
- Request metrics extraction (TPS, TTFT, tokens)
- SharedState for runtime metrics (current_requests)
- **Gaps:**
  - No structured metrics export (Prometheus/StatsD) despite .env mentioning it
  - No distributed tracing (OpenTelemetry/Jaeger) despite .env mentioning it
  - No health check endpoint
  - No log rotation or size management for event logs
  - Scheduler allocation logging is debug-only

### Dim 10: Performance & Scalability -- Score: 8/10

**Findings:**
- Core design is performance-oriented: pipeline parallel inference, continuous batching, KV cache management
- Dynamic layer allocation with DP optimization for latency minimization
- Multiple attention backends (FlashInfer, Triton, FA3, torch_native)
- KV cache memory management with configurable ratios
- Micro-batching to control memory pressure
- Prefix caching for repeated prompt optimization
- Benchmark tooling included (`src/backend/benchmark/`)
- Cross-platform GPU/MLX support with appropriate memory management per device
- **Gaps:** No auto-tuning, no load testing results in docs, no performance regression tests in CI

### Dim 11: Documentation & DX -- Score: 6/10

**Findings:**
- README covers overview, installation, supported models
- User guide: install.md and quick_start.md with step-by-step instructions and FAQ
- CONTRIBUTING.md, CHANGELOG.md, VERSIONING.md, UPSTREAM.md, RELEASING.md
- SECURITY.md with disclosure guidance
- CLI `--help` output is comprehensive
- `.env.example` documents all configuration options
- **Gaps:**
  - No API reference documentation
  - No architecture/design doc explaining scheduler, allocation, routing internals
  - Code docstrings are inconsistent -- some modules have thorough docstrings (scheduler, layer_allocation), others have minimal or none
  - No troubleshooting guide beyond FAQ in quick_start
  - No developer setup guide (beyond basic install)

### Dim 12: CI/CD & DevOps -- Score: 7/10

**Findings:**
- GitHub Actions CI: lint (ruff), format (black), type check (mypy, non-blocking), tests with coverage, codecov upload
- Matrix testing: ubuntu + macOS, Python 3.11/3.12/3.13
- Security job: bandit scan, safety dependency check
- Docker job: build + smoke test (`toolkit-mesh --help`)
- Docker build images workflow for Docker Hub
- Pre-commit hooks: check-yaml, end-of-file-fixer, trailing-whitespace, autoflake, isort, black
- **Gaps:**
  - mypy is `continue-on-error: true` with `|| true` -- effectively disabled
  - Bandit/safety scans are `continue-on-error: true` -- non-blocking
  - No release automation (no tag-based publishing workflow)
  - No Dependabot configuration
  - `build-images.yaml` still references upstream namespace `gradientservice/parallax`

### Dim 13: Error Handling & Resilience -- Score: 6/10

**Findings:**
- Graceful shutdown in CLI with SIGINT -> SIGTERM -> SIGKILL escalation
- Request timeout enforcement in scheduler (configurable, default 600s)
- Node heartbeat timeout detection with automatic leave
- Error isolation in event logging (never breaks inference)
- HTTP handler has error responses with typed error codes
- Executor factory has proper shutdown in finally blocks
- **Gaps:**
  - No circuit breaker for P2P communication failures
  - No retry logic for transient failures in HuggingFace downloads
  - `upload_package_info()` silently swallows all exceptions
  - No backpressure mechanism when request queue grows unbounded

### Dim 14: Data Management -- Score: 4/10

**Findings:**
- Event log is append-only JSONL with thread-safe writes (Lock)
- KV cache has explicit allocation/deallocation lifecycle
- Model weights managed through HuggingFace Hub + selective download
- **Gaps:**
  - No log rotation or retention policy
  - No data migration strategy for schema changes
  - No backup/recovery for event logs
  - No cache persistence across restarts

### Dim 15: UI/UX -- Score: 3/10

**Findings:**
- Frontend exists (pre-built dist in `src/frontend/dist/`) with chat interface and node config UI
- ASCII art display on startup
- CLI has `--help` with examples
- **Gap:** Frontend is upstream pre-built bundle, not customizable. Weight is 0% so not material.

### Dim 16: Internationalization -- Score: 0/10

Not applicable (weight = 0%). No i18n support, no translated strings. Appropriate for a developer tool.

### Dim 17: Accessibility -- Score: 0/10

Not applicable (weight = 0%). Frontend is upstream and not audited for a11y.

### Dim 18: Compliance & Licensing -- Score: 8/10

**Findings:**
- Apache 2.0 LICENSE file present
- NOTICE file with upstream attribution
- UPSTREAM.md documents fork origin with commit hash
- VERSIONING.md with SemVer policy
- RELEASING.md (release process)
- Bandit config in pyproject.toml with justified skip reasons
- **Gap:** No SBOM generation, no dependency license audit, no export control documentation

### Dim 19: Extensibility & Plugin Architecture -- Score: 7/10

**Findings:**
- Executor factory pattern supports pluggable backends (MLX, SGLang, vLLM)
- Layer allocator strategy pattern (Greedy, DP) with shared base class
- Request routing strategy pattern (RoundRobin, DP) with ABC interface
- Model implementations are modular (each in separate file)
- CLI passes through unknown args to underlying scripts
- **Gaps:**
  - No formal plugin API for adding new backends without modifying factory.py
  - No hook system for middleware/interceptors
  - No configuration file support (everything is CLI args)

### Dim 20: Deployment & Packaging -- Score: 7/10

**Findings:**
- `pyproject.toml` with proper metadata, entry points (`toolkit-mesh`, `parallax`)
- Optional dependency groups: `[mac]`, `[gpu]`, `[vllm]`, `[benchmark]`, `[dev]`
- Python version pinned: `>=3.11,<3.14`
- Docker: Dockerfile based on `lmsysorg/sglang:v0.5.5`, Dockerfile.spark for DGX Spark
- Docker build CI workflow
- `.env.example` for deployment configuration
- **Gaps:**
  - No PyPI publishing workflow
  - No Helm chart or Kubernetes manifests
  - No docker-compose for multi-node development setup
  - Build images workflow pushes to upstream Docker Hub namespace

### Dim 21: Agentic / Workspace -- Score: 2/10

**Findings:**
- This is an inference engine, not an agentic workspace
- No agent orchestration, no tool use, no workspace features
- The tool is consumed by agents (like NOVA) but does not itself exhibit agentic behavior
- Minimal score for providing an OpenAI-compatible API that agents can call
- Weight is only 2% -- appropriate.

---

## Archetype Minimum Compliance

| Dimension | Minimum | Actual | Status |
|-----------|---------|--------|--------|
| Dim 4: Domain Model Depth | 7 | 8 | PASS |
| Dim 7: Testing & QA | 7 | 6 | **FAIL** |
| Dim 8: Security & Hardening | 6 | 6 | PASS |
| Dim 10: Performance & Scalability | 6 | 8 | PASS |
| Dim 11: Documentation & DX | 6 | 6 | PASS |
| Dim 12: CI/CD & DevOps | 6 | 7 | PASS |

**1 minimum gap: Dim 7 must reach 7.**

---

## Gap Analysis & Sprint Tasks

### Sprint 0: Close Minimum Gap (Dim 7: Testing 6 -> 7)

| # | Task | Dimension | Priority |
|---|------|-----------|----------|
| S0-1 | Enforce mypy in CI (remove `continue-on-error` and `\|\| true`; fix type errors) | 7 | P0 |
| S0-2 | Add coverage threshold gate (e.g., `--cov-fail-under=60`) in CI | 7 | P0 |
| S0-3 | Add tests for cache_manager.py, radix_cache.py, shared_state.py | 7 | P0 |
| S0-4 | Expand test_prefix_cache.py from 32 lines to meaningful coverage | 7 | P1 |
| S0-5 | Add CLI integration test (subprocess run of `toolkit-mesh --help`, `toolkit-mesh run --help`) | 7 | P1 |

### Sprint 1: Security & Observability (Dim 8: 6->7, Dim 9: 5->7)

| # | Task | Dimension | Priority |
|---|------|-----------|----------|
| S1-1 | Add optional API key middleware for HTTP endpoints | 8 | P1 |
| S1-2 | Replace CORS `allow_origins=["*"]` with configurable allowlist | 8 | P1 |
| S1-3 | Make bandit/safety scans blocking in CI (remove `continue-on-error`) | 8 | P1 |
| S1-4 | Add Dependabot configuration (`.github/dependabot.yml`) | 8 | P1 |
| S1-5 | Add `/health` and `/ready` endpoints to both HTTP servers | 9 | P1 |
| S1-6 | Add Prometheus metrics endpoint (request count, latency histogram, cache hit rate) | 9 | P1 |
| S1-7 | Add log rotation for JSONL event log (size-based or time-based) | 9 | P2 |

### Sprint 2: Documentation & DX (Dim 11: 6->7)

| # | Task | Dimension | Priority |
|---|------|-----------|----------|
| S2-1 | Write architecture doc explaining scheduler, allocation, routing pipeline | 11 | P1 |
| S2-2 | Add API reference for `/v1/chat/completions` and scheduler management endpoints | 11 | P1 |
| S2-3 | Standardize docstrings across all Python modules (Google style) | 11 | P2 |
| S2-4 | Add developer setup guide with local testing workflow | 11 | P2 |

### Sprint 3: CI/CD & Packaging (Dim 12: 7->8, Dim 20: 7->8)

| # | Task | Dimension | Priority |
|---|------|-----------|----------|
| S3-1 | Fix Docker Hub namespace in build-images.yaml to Akiva org | 12 | P1 |
| S3-2 | Add PyPI publish workflow (on tag) | 12/20 | P2 |
| S3-3 | Add docker-compose.yml for multi-node local dev | 20 | P2 |
| S3-4 | Add release automation (tag -> build -> publish -> changelog) | 12 | P2 |

---

## Accepted Exceptions

| Item | Reason |
|------|--------|
| No auth in HTTP server | Developer tool; SECURITY.md documents deployer responsibility |
| No multi-tenancy | Not a design goal for Archetype 9 |
| No billing | Not applicable |
| No i18n/a11y | Developer CLI tool, no end-user UI |
| Frontend not audited | Upstream pre-built bundle, not customizable |
| Upstream telemetry (`upload_package_info`) | Inherited from fork; `--skip-upload` flag available |

---

## Audit Methodology

- Read all Python source files (24,816 LOC across ~90 files)
- Read all test files (3,242 LOC across 17 files)
- Read all CI/CD workflows (5 GitHub Actions files)
- Read all documentation files (README, user guides, security, contributing, versioning)
- Read Docker configuration (2 Dockerfiles)
- Read pyproject.toml for dependency and packaging analysis
- Grep for security anti-patterns (eval, exec, shell=True, hardcoded secrets)
- Verified against Archetype 9 weights and minimums
