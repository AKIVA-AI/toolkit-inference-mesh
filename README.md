<!--
Toolkit Fork Note:
- This folder is an Toolkit-branded fork of Parallax by GradientHQ.
- See `UPSTREAM.md` for the upstream commit reference and update workflow.
-->

# Toolkit Inference Mesh (Fork of Parallax)

Upstream: `GradientHQ/parallax` @ `143a2853fb88ec59fc593909f8554f8ea1c18923` (Apache-2.0).

## Overview

This is an Toolkit-branded fork of Parallax focused on distributed inference across heterogeneous nodes (Mac/GPU/etc.).

- Primary CLI: `toolkit-mesh`
- Compatibility CLI alias: `parallax` (kept to preserve upstream docs/examples)

## About
Toolkit Inference Mesh is an Toolkit-branded fork of Parallax, a fully decentralized inference engine developed by
[Gradient](https://gradient.network). It lets you build your own AI cluster for model inference onto a set of
distributed nodes despite their varying configuration and physical location. Its core features include:

- **Host local LLM on personal devices**
- **Cross-platform support**
- **Pipeline parallel model sharding**
- **Dynamic KV cache management & continuous batching for Mac**
- **Dynamic request scheduling and routing for high performance**

The backend architecture:

* P2P communication powered by [Lattica](https://github.com/GradientHQ/lattica)
* GPU backend powered by [SGLang](https://github.com/sgl-project/sglang)
* MAC backend powered by [MLX LM](https://github.com/ml-explore/mlx-lm)

## User Guide

- [Installation](./docs/user_guide/install.md)
- [Getting Started](./docs/user_guide/quick_start.md)

## Commercialization

See `COMMERCIALIZATION.md` for OSS vs Pro strategy, pricing anchors, and competitive positioning.

## Toolkit extensions

See `TOOLKIT_EXTENSIONS_ROADMAP.md` for how Toolkit adds governance and integrations around the OSS engine.

## Toolkit inference event logging (for cost/latency analysis)

When launching the scheduler (`toolkit-mesh run`), you can enable JSONL event logging for requests to
`/v1/chat/completions`:

- `--toolkit-event-log <path>` writes events in schema v1
- `--toolkit-cost-per-1k-tokens-usd <float>` optionally populates `cost_usd` from token counts

Validate and analyze the resulting log with `toolkit-cost-optimizer`:

```bash
toolkit-opt validate --input events.jsonl
toolkit-opt summarize --input events.jsonl
```

## Toolkit CLI naming

This fork exposes the CLI as `toolkit-mesh` (alias: `parallax`).

## Contributing

We warmly welcome contributions! Please refer to our [Contributing Guide](./docs/CONTRIBUTING.md).

## Supported Models

| Model | Provider | Description |
|:------|:---------|:------------|
| DeepSeek | Deepseek | Advanced LLM series for research and production |
| MiniMax-M2 | MiniMax AI | Fast, cost-effective MoE model for coding and agentic workflows |
| GLM-4.6 | Z AI | Long context, coding and reasoning capabilities |
| Kimi-K2 | Moonshot AI | Open agentic model with 256k context window |
| Qwen | Qwen | Alibaba's model series with quantization support |
| gpt-oss | OpenAI | Open-weight GPT models with safety classification |
| Llama 3 | Meta | Open-source models in various sizes |
