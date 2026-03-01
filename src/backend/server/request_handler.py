import json
import time
from typing import Dict

import aiohttp
from fastapi import Request
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.concurrency import iterate_in_threadpool

from backend.server.constants import NODE_STATUS_AVAILABLE
from backend.server.toolkit_event_log import append_inference_event
from backend.server.toolkit_event_log import estimate_cost_usd
from parallax_utils.logging_config import get_logger
from parallax_utils.request_metrics import get_request_metrics

logger = get_logger(__name__)

AIOHTTP_TIMEOUT = aiohttp.ClientTimeout(total=20 * 60 * 60)


class RequestHandler:
    """HTTP request forwarder with scheduler-aware routing and retry logic.

    Behavior for routing resolution:
    - routing_table is None: scheduler has not decided yet -> treat as error for this attempt
    - routing_table is []: all pipelines are full now -> retry up to max attempts
    - routing_table is non-empty: forward to first hop
    """

    MAX_ROUTING_RETRY = 20
    RETRY_DELAY_SEC = 5

    def __init__(self):
        self.scheduler_manage = None
        self.stubs = {}

    def set_scheduler_manage(self, scheduler_manage):
        self.scheduler_manage = scheduler_manage

    def get_stub(self, node_id):
        if node_id not in self.stubs:
            self.stubs[node_id] = self.scheduler_manage.completion_handler.get_stub(node_id)
        return self.stubs[node_id]

    async def _forward_request(
        self,
        request_data: Dict,
        request_id: str,
        received_ts: int,
        request: Request | None = None,
    ):
        start_time = time.time()
        logger.debug(f"Forwarding request {request_id}; stream={request_data.get('stream', False)}")
        if (
            self.scheduler_manage is None
            or not self.scheduler_manage.get_schedule_status() == NODE_STATUS_AVAILABLE
        ):
            return JSONResponse(
                content={"error": "Server is not ready"},
                status_code=500,
            )

        # Try to resolve routing; retry if table is an empty list (capacity full)
        attempts = 0
        routing_table = None
        while attempts < self.MAX_ROUTING_RETRY:
            try:
                routing_table = self.scheduler_manage.get_routing_table(request_id, received_ts)
                logger.debug(
                    f"get_routing_table for request {request_id} return: {routing_table} (attempt {attempts+1})"
                )
            except Exception as e:
                logger.exception(f"get_routing_table error: {e}")
                return JSONResponse(
                    content={"error": "Get routing table error"},
                    status_code=500,
                )

            # None -> scheduler has not set yet; treat as hard error (no waiting here)
            if routing_table is None:
                return JSONResponse(
                    content={"error": "Routing pipelines not ready"},
                    status_code=503,
                )

            # Non-empty -> proceed
            if len(routing_table) > 0:
                break

            # Empty list -> capacity full now, retry after short delay
            attempts += 1
            if attempts < self.MAX_ROUTING_RETRY:
                # small async delay before re-forwarding
                import asyncio

                await asyncio.sleep(self.RETRY_DELAY_SEC)

        # If still empty after retries, return 429 Too Many Requests
        if routing_table is not None and len(routing_table) == 0:
            return JSONResponse(
                content={"error": "All pipelines are busy or not ready. Please retry later."},
                status_code=429,
            )

        # Add request_id and routing_table to request_data
        request_data["rid"] = str(request_id)
        request_data["routing_table"] = routing_table
        stub = self.get_stub(routing_table[0])
        is_stream = request_data.get("stream", False)
        try:
            if is_stream:

                async def stream_generator():
                    response = stub.chat_completion(request_data)
                    first_token_time = None
                    last_chunk = None
                    last_token_time = None
                    try:
                        iterator = iterate_in_threadpool(response)
                        async for chunk in iterator:
                            last_token_time = time.time()
                            if first_token_time is None:
                                first_token_time = last_token_time
                            if chunk is not None and not chunk.decode("utf-8").startswith(
                                "data: [DONE]"
                            ):
                                last_chunk = chunk
                            yield chunk
                    finally:
                        if last_chunk is not None:
                            tps, ttft, input_tokens, output_tokens = get_request_metrics(
                                last_chunk, start_time, first_token_time, last_token_time
                            )
                            if (
                                tps is not None
                                and ttft is not None
                                and input_tokens is not None
                                and output_tokens is not None
                            ):
                                logger.info(
                                    f"Request ID: {request_id} | TPS: {tps:.2f} |  TTFT: {ttft} ms | Output tokens: {output_tokens} | Input tokens: {input_tokens}"
                                )
                                self._emit_inference_event(
                                    request_id=str(request_id),
                                    model=str(request_data.get("model") or "unknown"),
                                    started_ts=float(start_time),
                                    status_code=200,
                                    success=True,
                                    tokens_in=int(input_tokens),
                                    tokens_out=int(output_tokens),
                                    meta={
                                        "ttft_ms": int(ttft),
                                        "tps": float(tps),
                                        "stream": True,
                                    },
                                    request=request,
                                )
                        else:
                            self._emit_inference_event(
                                request_id=str(request_id),
                                model=str(request_data.get("model") or "unknown"),
                                started_ts=float(start_time),
                                status_code=200,
                                success=True,
                                tokens_in=None,
                                tokens_out=None,
                                meta={"stream": True},
                                request=request,
                            )
                        logger.debug(f"client disconnected for {request_id}")
                        response.cancel()

                resp = StreamingResponse(
                    stream_generator(),
                    media_type="text/event-stream",
                    headers={
                        "X-Content-Type-Options": "nosniff",
                        "Cache-Control": "no-cache",
                    },
                )
                logger.debug(f"Streaming response initiated for {request_id}")
                return resp
            else:
                response = stub.chat_completion(request_data)
                content = (await anext(iterate_in_threadpool(response))).decode()
                logger.debug(f"Non-stream response completed for {request_id}")
                # response is a JSON string; parse to Python object before returning
                payload = json.loads(content)
                tokens_in = None
                tokens_out = None
                try:
                    usage = payload.get("usage") if isinstance(payload, dict) else None
                    if isinstance(usage, dict):
                        pi = usage.get("prompt_tokens")
                        po = usage.get("completion_tokens")
                        if isinstance(pi, int):
                            tokens_in = pi
                        if isinstance(po, int):
                            tokens_out = po
                except Exception:
                    pass

                self._emit_inference_event(
                    request_id=str(request_id),
                    model=str(request_data.get("model") or "unknown"),
                    started_ts=float(start_time),
                    status_code=200,
                    success=True,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    meta={"stream": False},
                    request=request,
                )

                if request is not None:
                    try:
                        request.state.toolkit_event_written = True
                    except Exception:
                        pass
                return JSONResponse(content=payload)
        except Exception as e:
            logger.exception(f"Error in _forward_request: {e}")
            self._emit_inference_event(
                request_id=str(request_id),
                model=str(request_data.get("model") or "unknown"),
                started_ts=float(start_time),
                status_code=500,
                success=False,
                tokens_in=None,
                tokens_out=None,
                meta={"error": str(e)},
                request=request,
            )
            if request is not None:
                try:
                    request.state.toolkit_event_written = True
                except Exception:
                    pass
            return JSONResponse(
                content={"error": "Internal server error"},
                status_code=500,
            )

    def _emit_inference_event(
        self,
        *,
        request_id: str,
        model: str,
        started_ts: float,
        status_code: int,
        success: bool,
        tokens_in: int | None,
        tokens_out: int | None,
        meta: dict[str, object],
        request: Request | None,
    ) -> None:
        try:
            now = time.time()
            elapsed_ms = int((now - started_ts) * 1000)
            tenant = ""
            project = ""
            tier = ""
            if request is not None:
                tenant = str(getattr(request.state, "tenant", "") or "")
                project = str(getattr(request.state, "project", "") or "")
                tier = str(getattr(request.state, "tier", "") or "")
                try:
                    request.state.toolkit_event_written = True
                except Exception:
                    pass

            event: dict[str, object] = {
                "schema_version": 1,
                "created_ts": float(started_ts),
                "request_id": request_id,
                "tenant": tenant,
                "project": project,
                "tier": tier,
                "provider": "parallax",
                "model": model or "unknown",
                "latency_ms": float(elapsed_ms),
                "cost_usd": float(estimate_cost_usd(tokens_in=tokens_in, tokens_out=tokens_out)),
                "success": bool(success),
                "error_type": "" if success else f"http_{status_code}",
                "meta": dict(meta),
            }
            if tokens_in is not None:
                event["tokens_in"] = int(tokens_in)
            if tokens_out is not None:
                event["tokens_out"] = int(tokens_out)
            append_inference_event(event)
        except Exception as e:
            logger.error(
                f"Failed to emit inference event for request {request_id}: {e}",
                exc_info=True,
            )

    async def v1_chat_completions(
        self, request_data: Dict, request_id: str, received_ts: int, request: Request | None = None
    ):
        return await self._forward_request(request_data, request_id, received_ts, request)
