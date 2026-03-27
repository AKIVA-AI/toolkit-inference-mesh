# Inference Mesh — Decentralized pipeline-parallel LLM serving with SGLang and MLX-LM

**Archetype:** 9 — Developer Tool / CLI Utility
**Standards:** Akiva Build Standard v2.13
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
- Audit Score: 65/100
- Tests: 29

## Key Rules
- Archetype 9: single-purpose CLI tool, zero or minimal dependencies in core
- Tests first, security fixes before features
- One task at a time, verified before moving to next
