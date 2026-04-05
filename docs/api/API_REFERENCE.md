# API Reference — toolkit-inference-mesh

**Version:** 0.1.2
**Base URL:** `http://{host}:{port}` (default: `http://localhost:8000`)

## Health & Operations

### GET /health

Liveness probe. Returns 200 if the process is running.

**Response:**
```json
{ "status": "ok", "version": "0.1.2" }
```

### GET /ready

Readiness probe. Returns 200 only when the scheduler is initialized and running.

**Response (200):**
```json
{ "status": "ready", "version": "0.1.2" }
```

**Response (503):**
```json
{ "status": "not_ready", "version": "0.1.2" }
```

### GET /metrics

Lightweight JSON metrics. Suitable for monitoring dashboards or Prometheus adapters.

**Response:**
```json
{
  "requests_total": 1042,
  "requests_success": 1038,
  "requests_error": 4,
  "uptime_seconds": 3600.5,
  "version": "0.1.2"
}
```

---

## Inference

### POST /v1/chat/completions

OpenAI-compatible chat completions endpoint. Supports streaming and non-streaming modes.

**Headers:**
| Header | Required | Description |
|--------|----------|-------------|
| `Content-Type` | Yes | `application/json` |
| `x-tenant` | No | Tenant identifier (logged in events) |
| `x-project` | No | Project identifier (logged in events) |

**Request Body:**
```json
{
  "model": "deepseek-v3",
  "messages": [
    { "role": "system", "content": "You are a helpful assistant." },
    { "role": "user", "content": "Hello!" }
  ],
  "stream": true,
  "max_tokens": 1024,
  "temperature": 0.7,
  "top_p": 0.9,
  "akiva": {
    "tier": "standard"
  }
}
```

**Streaming Response (SSE):**
```
data: {"id":"chatcmpl-...","object":"chat.completion.chunk","choices":[{"delta":{"content":"Hello"},"index":0}]}

data: [DONE]
```

**Non-Streaming Response:**
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "model": "deepseek-v3",
  "choices": [
    {
      "index": 0,
      "message": { "role": "assistant", "content": "Hello! How can I help?" },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 12,
    "completion_tokens": 8,
    "total_tokens": 20
  }
}
```

**Error Response:**
```json
{
  "error": {
    "message": "Request not found",
    "type": "RequestNotFoundError",
    "code": 404
  }
}
```

---

## Scheduler Management

### POST /scheduler/init

Initialize or reinitialize the scheduler with a model.

**Request Body:**
```json
{
  "model_name": "deepseek-ai/DeepSeek-V3",
  "init_nodes_num": 2,
  "is_local_network": false
}
```

**Response (200):**
```json
{
  "type": "scheduler_init",
  "data": {
    "model_name": "deepseek-ai/DeepSeek-V3",
    "init_nodes_num": 2,
    "is_local_network": false
  }
}
```

### GET /cluster/status

Server-Sent Events stream of cluster status. Emits JSON every 1 second.

**Response (NDJSON stream):**
```json
{"nodes": [...], "model": "deepseek-v3", "status": "running"}
```

### GET /model/list

List available models.

**Response:**
```json
{
  "type": "model_list",
  "data": [
    { "name": "deepseek-ai/DeepSeek-V3", "params": "671B" },
    { "name": "Qwen/Qwen3-32B", "params": "32B" }
  ]
}
```

### GET /node/join/command

Get the CLI command for joining a node to the cluster.

**Response:**
```json
{
  "type": "node_join_command",
  "data": "toolkit-mesh join --initial-peers /dns4/.../p2p/..."
}
```

---

## Configuration

### CORS

By default, CORS allows all origins (`*`). Set `CORS_ALLOWED_ORIGINS` environment variable
to restrict:

```bash
export CORS_ALLOWED_ORIGINS="https://app.example.com,http://localhost:3000"
```

### Event Logging

Enable JSONL event logging:

```bash
toolkit-mesh run --toolkit-event-log ~/.akiva/inference-events.jsonl \
                 --toolkit-cost-per-1k-tokens-usd 0.01
```

Events are appended as line-delimited JSON with schema version 1.

---

## Peer HTTP Server

Each inference peer exposes a lightweight HTTP server (separate from the backend scheduler).

### GET /health

Liveness probe for the peer node.

**Response:**
```json
{ "status": "ok" }
```

### POST /v1/chat/completions

Same OpenAI-compatible endpoint as the backend, but routes directly to the local executor
(used when connecting to a peer directly, not through the scheduler).
