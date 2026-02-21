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
- **Dynamic KV cache management and continuous batching for Mac**
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

See `Toolkit_EXTENSIONS_ROADMAP.md` for how Toolkit adds governance and integrations around the OSS engine.

## Toolkit inference event logging (for cost/latency analysis)

When launching the scheduler (`toolkit-mesh run`), you can enable JSONL event logging for requests to
`/v1/chat/completions`:

- `--toolkit-event-log <path>` writes events in schema v1 (see `docs/enterprise-tools/schemas/toolkit_inference_event.schema.json`)
- `--toolkit-cost-per-1k-tokens-usd <float>` optionally populates `cost_usd` from token counts

Validate and analyze the resulting log with `enterprise-tools/cost-latency-optimizer/`:

```bash
toolkit-opt validate --input events.jsonl
toolkit-opt summarize --input events.jsonl
```

## Toolkit CLI naming

This fork exposes the CLI as `toolkit-mesh` (alias: `parallax`).

## Contributing

We warmly welcome contributions of all kinds! For guidelines on how to get involved, please refer to our [Contributing Guide](./docs/CONTRIBUTING.md).

## Supported Models

| Model | Provider | HuggingFace Collection | Blog | Description |
|:-------------|:-------------|:----------------------------:|:----------------------------:|:----------------------------|
| DeepSeek | Deepseek | [DeepSeek-V3.1](https://huggingface.co/collections/deepseek-ai/deepseek-v31) [DeepSeek-R1](https://huggingface.co/collections/deepseek-ai/deepseek-r1) [DeepSeek-V3](https://huggingface.co/collections/deepseek-ai/deepseek-v3) [DeepSeek-V2](https://huggingface.co/collections/deepseek-ai/deepseek-v2) | [DeepSeek V3.1: The New Frontier in Artificial Intelligence](https://deepseek.ai/blog/deepseek-v31) | Advanced large language model series from Deepseek AI with multiple generations. |
| MiniMax-M2 | MiniMax AI | [MiniMax-M2](https://huggingface.co/MiniMaxAI/MiniMax-M2) | [MiniMax M2 and Agent: Ingenious in Simplicity](https://www.minimax.io/news/minimax-m2) | Compact, fast, and cost-effective MoE model (230B parameters, 10B active). |
| GLM-4.6 | Z AI | [GLM-4.6](https://huggingface.co/zai-org/GLM-4.6) | [GLM-4.6: Advanced Agentic, Reasoning and Coding Capabilities](https://z.ai/blog/glm-4.6) | Improves upon GLM-4.5 with longer 200K token context window. |
| Kimi-K2 | Moonshot AI | [Kimi-K2](https://huggingface.co/collections/moonshotai/kimi-k2-6871243b990f2af5ba60617d) | [Kimi K2: Open Agentic Intelligence](https://moonshotai.github.io/Kimi-K2/) | Kimi-K2 model family for deep, step-by-step reasoning. |
| Qwen | Qwen | [Qwen3-Next](https://huggingface.co/collections/Qwen/qwen3-next-68c25fd6838e585db8eeea9d) [Qwen3](https://huggingface.co/collections/Qwen/qwen3-67dd247413f0e2e4f653967f) [Qwen2.5](https://huggingface.co/collections/Qwen/qwen25-66e81a666513e518adb90d9e) | [Qwen3-Next: Towards Ultimate Training and Inference Efficiency](https://qwen.ai/blog?id=4074cca80393150c248e508aa62983f9cb7d27cd) | Family of large language models developed by Alibaba. |
| gpt-oss | OpenAI | [gpt-oss](https://huggingface.co/collections/openai/gpt-oss-68911959590a1634ba11c7a4) [gpt-oss-safeguard](https://huggingface.co/collections/openai/gpt-oss-safeguard) | [Introducing gpt-oss-safeguard](https://openai.com/index/introducing-gpt-oss-safeguard/) | OpenAI's open-weight GPT models (20B and 120B). |
| Meta Llama 3 | Meta | [Meta Llama 3](https://huggingface.co/collections/meta-llama/meta-llama-3-66214712577ca38149ebb2b6) [Llama 3.1](https://huggingface.co/collections/meta-llama/llama-31-669fc079a0c406a149a5738f) [Llama 3.2](https://huggingface.co/collections/meta-llama/llama-32-66f448ffc8c32f949b04c8cf) [Llama 3.3](https://huggingface.co/collections/meta-llama/llama-33-67531d5c405ec5d08a852000) | [Introducing Meta Llama 3](https://ai.meta.com/blog/meta-llama-3/) | Meta's third-generation Llama model, available in 8B and 70B parameters. |
