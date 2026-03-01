import asyncio
import json
import time
import uuid
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from backend.server.request_handler import RequestHandler
from backend.server.toolkit_event_log import (
    append_inference_event,
    set_cost_per_1k_tokens_usd,
    set_event_log_path,
)
from backend.server.scheduler_manage import SchedulerManage
from backend.server.server_args import parse_args
from backend.server.static_config import (
    get_model_list,
    get_node_join_command,
    init_model_info_dict_cache,
)
from parallax_utils.ascii_anime import display_parallax_run
from parallax_utils.file_util import get_project_root
from parallax_utils.logging_config import get_logger, set_log_level
from parallax_utils.version_check import check_latest_release

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = get_logger(__name__)

scheduler_manage = None
request_handler = RequestHandler()


@app.middleware("http")
async def toolkit_inference_event_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    started = time.time()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = int(getattr(response, "status_code", 200))
        return response
    finally:
        try:
            # Only emit events for the OpenAI-compatible endpoint (keeps noise down).
            if request.url.path != "/v1/chat/completions":
                return
            if bool(getattr(request.state, "toolkit_event_written", False)):
                return

            elapsed_ms = int((time.time() - started) * 1000)
            model = str(getattr(request.state, "model", "") or "")
            req_id = str(getattr(request.state, "request_id", "") or "")
            tier = str(getattr(request.state, "tier", "") or "")
            tenant = str(getattr(request.state, "tenant", "") or "") or request.headers.get(
                "x-tenant", ""
            )
            project = str(getattr(request.state, "project", "") or "") or request.headers.get(
                "x-project", ""
            )

            # Cost is unknown at this layer; set to 0.0 until a pricing model is introduced.
            event = {
                "schema_version": 1,
                "created_ts": float(started),
                "request_id": req_id,
                "tenant": tenant,
                "project": project,
                "tier": tier,
                "provider": "parallax",
                "model": model or "unknown",
                "latency_ms": float(elapsed_ms),
                "cost_usd": 0.0,
                "success": bool(200 <= status_code < 400),
                "error_type": "" if 200 <= status_code < 400 else f"http_{status_code}",
                "meta": {"path": request.url.path, "status_code": status_code},
            }
            append_inference_event(event)
            try:
                request.state.toolkit_event_written = True
            except Exception:
                pass
        except Exception:
            # Never break serving due to telemetry.
            return


@app.get("/model/list")
async def model_list():
    return JSONResponse(
        content={
            "type": "model_list",
            "data": get_model_list(),
        },
        status_code=200,
    )


@app.post("/scheduler/init")
async def scheduler_init(raw_request: Request):
    request_data = await raw_request.json()
    model_name = request_data.get("model_name")
    init_nodes_num = request_data.get("init_nodes_num")
    is_local_network = request_data.get("is_local_network")

    # Validate required parameters
    if model_name is None:
        return JSONResponse(
            content={
                "type": "scheduler_init",
                "error": "model_name is required",
            },
            status_code=400,
        )
    if init_nodes_num is None:
        return JSONResponse(
            content={
                "type": "scheduler_init",
                "error": "init_nodes_num is required",
            },
            status_code=400,
        )

    try:
        # If scheduler is already running, stop it first
        if scheduler_manage.is_running():
            logger.info(f"Stopping existing scheduler to switch to model: {model_name}")
            scheduler_manage.stop()

        # Start scheduler with new model
        logger.info(
            f"Initializing scheduler with model: {model_name}, init_nodes_num: {init_nodes_num}"
        )
        scheduler_manage.run(model_name, init_nodes_num, is_local_network)

        return JSONResponse(
            content={
                "type": "scheduler_init",
                "data": {
                    "model_name": model_name,
                    "init_nodes_num": init_nodes_num,
                    "is_local_network": is_local_network,
                },
            },
            status_code=200,
        )
    except Exception as e:
        logger.exception(f"Error initializing scheduler: {e}")
        return JSONResponse(
            content={
                "type": "scheduler_init",
                "error": str(e),
            },
            status_code=500,
        )


@app.get("/node/join/command")
async def node_join_command():
    peer_id = scheduler_manage.get_peer_id()
    is_local_network = scheduler_manage.get_is_local_network()

    return JSONResponse(
        content={
            "type": "node_join_command",
            "data": get_node_join_command(peer_id, is_local_network),
        },
        status_code=200,
    )


@app.get("/cluster/status")
async def cluster_status():
    async def stream_cluster_status():
        while True:
            yield json.dumps(scheduler_manage.get_cluster_status(), ensure_ascii=False) + "\n"
            await asyncio.sleep(1)

    return StreamingResponse(
        stream_cluster_status(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.post("/v1/chat/completions")
async def openai_v1_chat_completions(raw_request: Request):
    request_data = await raw_request.json()
    request_id = str(uuid.uuid4())
    received_ts = time.time()
    try:
        raw_request.state.model = str(request_data.get("model") or "")
        raw_request.state.request_id = request_id
        raw_request.state.tier = str((request_data.get("akiva") or {}).get("tier", "") or "")
        raw_request.state.tenant = str(raw_request.headers.get("x-tenant", "") or "")
        raw_request.state.project = str(raw_request.headers.get("x-project", "") or "")
    except Exception:
        pass
    return await request_handler.v1_chat_completions(
        request_data, request_id, received_ts, raw_request
    )


# Disable caching for index.html
@app.get("/")
async def serve_index():
    response = FileResponse(str(get_project_root()) + "/src/frontend/dist/index.html")
    # Disable cache
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# mount the frontend
app.mount(
    "/",
    StaticFiles(directory=str(get_project_root() / "src" / "frontend" / "dist"), html=True),
    name="static",
)

if __name__ == "__main__":
    args = parse_args()
    set_log_level(args.log_level)
    logger.info(f"args: {args}")

    if getattr(args, "toolkit_event_log", ""):
        try:
            p = Path(str(args.toolkit_event_log))
            set_event_log_path(p)
            logger.info(f"Toolkit inference event log enabled: {p}")
        except ValueError as e:
            logger.error(f"Invalid event log path: {e}")
            raise

        cost_per_1k = float(getattr(args, "toolkit_cost_per_1k_tokens_usd", None) or 0.0)
        try:
            set_cost_per_1k_tokens_usd(cost_per_1k)
            if cost_per_1k > 0:
                logger.info(
                    f"Toolkit inference event cost estimator enabled: "
                    f"${cost_per_1k:.4f} / 1k tokens"
                )
        except ValueError as e:
            logger.error(f"Invalid cost per 1K tokens: {e}")
            raise

    if args.model_name is None:
        init_model_info_dict_cache(args.use_hfcache)

    if args.log_level != "DEBUG":
        display_parallax_run()

    check_latest_release()

    scheduler_manage = SchedulerManage(
        initial_peers=args.initial_peers,
        relay_servers=args.relay_servers,
        dht_prefix=args.dht_prefix,
        host_maddrs=[
            f"/ip4/0.0.0.0/tcp/{args.tcp_port}",
            f"/ip4/0.0.0.0/udp/{args.udp_port}/quic-v1",
        ],
        announce_maddrs=args.announce_maddrs,
        http_port=args.port,
        use_hfcache=args.use_hfcache,
    )

    request_handler.set_scheduler_manage(scheduler_manage)

    model_name = args.model_name
    init_nodes_num = args.init_nodes_num
    is_local_network = args.is_local_network
    if model_name is not None and init_nodes_num is not None:
        scheduler_manage.run(model_name, init_nodes_num, is_local_network)

    host = args.host
    port = args.port

    uvicorn.run(app, host=host, port=port, log_level="info", loop="uvloop")
