# Inference Mesh — Decentralized pipeline-parallel LLM serving with SGLang and MLX-LM

**Archetype:** 9 — Developer Tool / CLI Utility
**Standards:** Akiva Build Standard v2.14
**Ontology ID:** TK-09

## Stack
- Language: Python 3.11-3.13
- Test: `pytest -xvs`
- Lint: `black src/ tests/ && ruff check src/ tests/`
- Build: `pip install -e .`

## Verification Commands
| Command | Purpose |
|---------|---------|
| `pytest -xvs` | Run tests |
| `black src/ tests/ && ruff check src/ tests/` | Lint |

## Current State
- Audit Score: 59.8/100 (v2.14, 2026-04-04) — prior 64.8/100 (v2.13, delta from dimension model change)
- Post-sprint projected: ~65/100 (D4→7, D7→7, D8→7, D9→6, D11→7)
- Tests: 238 passing
- Minimum Gaps: D4 and D7 closed by sprint (health endpoints, CORS, coverage threshold, mypy enforcement)

## Sprint Changelog (2026-04-05)
- D7: CI coverage threshold raised 3%→60%, mypy enforced (non-blocking removed), security scans enforced
- D8: SBOM generation (Syft + Grype) added to CI, CORS hardened with `CORS_ALLOWED_ORIGINS` env var
- D4/D9: `/health`, `/ready`, `/metrics` endpoints added to backend + peer HTTP server
- D11: `docs/CODEBASE_MAP.md`, `docs/api/API_REFERENCE.md`, `.github/ISSUE_TEMPLATE/`, `.github/PULL_REQUEST_TEMPLATE.md` created
- Bug fix: middleware `return` inside `finally` caused 500 on non-chat endpoints (pre-existing)
- Test infra: `mock_hw_deps.py` fixed for `find_spec` ValueError on stubbed modules

## Human-Required Actions
> These items cannot be completed by an agent and require human intervention.

| Action | Dimension Impact | Context |
|--------|-----------------|---------|
| GPU CI runners | D7 capped at 7 | E2E integration tests require CUDA hardware |
| Penetration testing | D19 capped at 6 | External security vendor engagement |
| mTLS for P2P layer | D18 capped at 3 | Architecture decision + cert infrastructure |
| Domain expert review | D12 capped at 8 | Validate model implementations against reference |
| Production deployment | D20 capped at 5 | Infrastructure provisioning + monitoring setup |

## Key Rules
- Archetype 9: single-purpose CLI tool, zero or minimal dependencies in core
- Tests first, security fixes before features
- One task at a time, verified before moving to next
