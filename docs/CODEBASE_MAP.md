# Codebase Map — toolkit-inference-mesh

**Version:** 0.1.2
**Updated:** 2026-04-04
**Archetype:** 9 — Developer Tool / CLI Utility

## Overview

Decentralised pipeline-parallel LLM inference mesh. Routes inference across heterogeneous
nodes (CUDA via SGLang/vLLM, Apple Silicon via MLX) using P2P networking (Lattica/libp2p).
Forked from Parallax with Akiva toolkit enhancements.

## Directory Structure

```
toolkit-inference-mesh/
├── src/
│   ├── parallax/              # Core inference engine (9,700 LOC)
│   │   ├── cli.py             # CLI entry point: run/join/chat subcommands
│   │   ├── launch.py          # Process spawning + signal handling
│   │   ├── control_plane/     # Akiva control-plane contracts (optional framework integration)
│   │   ├── server/            # Inference execution layer (3,870 LOC)
│   │   │   ├── http_server.py # FastAPI peer HTTP server (OpenAI-compatible API)
│   │   │   ├── scheduler.py   # Continuous batching scheduler (2-phase: admission + batching)
│   │   │   ├── shard_loader.py# HuggingFace weight loading + selective download
│   │   │   ├── radix_cache.py # Prefix caching (radix tree)
│   │   │   ├── cache_manager.py # KV cache allocation/deallocation
│   │   │   ├── request.py     # Request lifecycle state machine
│   │   │   └── executor/      # Backend executors (MLX, SGLang, vLLM) with factory pattern
│   │   ├── p2p/               # P2P networking via Lattica (1,200 LOC)
│   │   │   ├── server.py      # RPC methods for inter-peer hidden state forwarding
│   │   │   ├── message_util.py# Protobuf message serialization
│   │   │   └── proto/         # Generated protobuf definitions
│   │   ├── models/            # 12 model implementations (DeepSeek, Qwen, Llama, etc.)
│   │   ├── utils/             # Utilities (995 LOC)
│   │   ├── sglang/            # SGLang monkey patches
│   │   ├── vllm/              # vLLM monkey patches
│   │   └── metal/             # CUDA kernel wrappers
│   ├── scheduling/            # Distributed scheduling layer (880 LOC)
│   │   ├── scheduler.py       # Orchestration: node join/leave, request dispatch
│   │   ├── layer_allocation.py# DP + Greedy layer allocation strategies
│   │   ├── request_routing.py # DP + Round-robin request routing strategies
│   │   └── node.py            # Node state + hardware info
│   ├── backend/               # Toolkit HTTP scheduler (500 LOC)
│   │   ├── main.py            # FastAPI app: /health, /ready, /metrics, /v1/chat/completions
│   │   └── server/            # Request handler, event logging, scheduler management
│   ├── parallax_utils/        # Shared utilities (800 LOC)
│   │   ├── logging_config.py  # Structured colored logging with package filtering
│   │   ├── request_metrics.py # TPS/TTFT metrics
│   │   └── shared_state.py    # Thread-safe runtime metrics
│   └── frontend/              # React+TypeScript UI (upstream, pre-built)
├── tests/                     # ~150+ tests, 30 files, 6,148 LOC
│   ├── conftest.py            # Global fixtures, hardware mocking (809 LOC)
│   ├── scheduler_tests/       # Layer allocation, routing, scheduler lifecycle
│   ├── test_akiva_enhancements.py # 25 tests for toolkit event logging
│   └── [27 more test files]
├── docker/                    # Dockerfile, Dockerfile.spark
├── .github/
│   ├── workflows/             # CI, build-images, pre-commit, commit-check
│   ├── dependabot.yml
│   ├── ISSUE_TEMPLATE/        # Bug report, feature request
│   └── PULL_REQUEST_TEMPLATE.md
└── docs/
    ├── audits/                # Audit reports
    ├── user_guide/            # install.md, quick_start.md
    └── api/                   # API reference
```

## Key Modules

| Module | Entry Point | Purpose |
|--------|-------------|---------|
| CLI | `parallax.cli:main` | `toolkit-mesh run\|join\|chat` commands |
| Backend Server | `backend.main:app` | Scheduler HTTP server (FastAPI) |
| Peer Server | `parallax.server.http_server:app` | Per-node inference server |
| Scheduling | `scheduling.scheduler:Scheduler` | Node orchestration + request dispatch |
| Layer Allocation | `scheduling.layer_allocation` | DP/Greedy layer-to-node assignment |
| Request Routing | `scheduling.request_routing` | DP/RoundRobin request path selection |
| Executor Factory | `parallax.server.executor.factory` | MLX/SGLang/vLLM backend selection |
| Event Logging | `backend.server.toolkit_event_log` | JSONL inference event telemetry |
| Control Plane | `parallax.control_plane.contracts` | Akiva execution contracts (optional) |

## Data Flow

```
Client → Backend /v1/chat/completions
  → RequestHandler → Scheduler.dispatch_next_request()
    → LayerAllocator assigns [start, end) layers per node
    → RequestRouter finds optimal path (Dijkstra/DP)
      → Peer 0 (tokenize + prefill layers [0, N))
        → Peer 1..K (forward hidden states, P2P/Protobuf)
          → Last Peer (decode + sample token → stream back to Peer 0)
            → Client (SSE stream)
```

## Test Coverage Map

| Area | Test Files | Coverage |
|------|-----------|----------|
| Scheduling | 4 files (~1,100 LOC) | Layer allocation, routing, scheduler lifecycle |
| Toolkit Enhancements | 1 file (435 LOC, 25 tests) | Event logging, cost estimation, path traversal |
| Cache Management | 3 files | KV cache, radix cache, prefix cache |
| Executor | 1 file | Factory pattern, lifecycle, process management |
| HTTP Handler | 1 file | Request/response, streaming, error handling |
| P2P Messaging | 1 file | Protobuf serialization |
| Models | 2 files | Model instantiation, model info |
| Routing Edge Cases | 1 file | Warm-up truncation, shard dropping |
| Shared State | 1 file | Thread-safe metrics |

## External Dependencies (Critical)

| Package | Version | Role |
|---------|---------|------|
| lattica | ==1.0.14 | P2P networking (libp2p wrapper) |
| transformers | ==4.57.1 | Tokenizers, model configs |
| protobuf | ==6.31.1 | Inter-peer message serialization |
| torch | ==2.8.0 (mac) | PyTorch inference |
| sglang | ==0.5.9 (gpu) | CUDA inference engine |
| vllm | ==0.11.0 (vllm) | Alternative CUDA inference engine |
| mlx/mlx-lm | ==0.30.0/0.28.4 | Apple Silicon inference |

## Human-Required Actions

> These items cannot be completed by an agent and require human intervention.

| Action | Context |
|--------|---------|
| GPU CI runners | E2E integration tests require CUDA hardware |
| Penetration testing | External security vendor engagement |
| mTLS for P2P layer | Architecture decision + certificate infrastructure |
| Domain expert review | Validate model implementations against reference |
| Production deployment | Infrastructure provisioning + monitoring setup |
| Supabase push | If migrations are added in future sprints |
