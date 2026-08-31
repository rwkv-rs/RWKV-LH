"""Loopback HTTP service for the persistent, project-owned State Router."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping

from rwkv_lh.inference.vllm_rwkv import PersistentVLLMRWKVExtractor
from rwkv_lh.state_router.http_client import (
    ROUTER_SERVICE_HEALTH_SCHEMA,
    ROUTER_SERVICE_REQUEST_SCHEMA,
    ROUTER_SERVICE_RESPONSE_SCHEMA,
)
from rwkv_lh.state_router.local_backend import (
    DEFAULT_ROUTER_MODEL,
    DEFAULT_VLLM_RWKV_PYTHON,
    DEFAULT_VLLM_RWKV_REVISION,
    DEFAULT_VLLM_RWKV_ROOT,
    LocalVLLMRWKVSettings,
)
from rwkv_lh.state_router.model import MultiHeadMLPArtifact, StateRouter
from rwkv_lh.state_router.protocol import RouterInput
from rwkv_lh.state_router.shadow import DEFAULT_SHADOW_HEAD, DEFAULT_SHADOW_PROJECTION
from rwkv_lh.state_router.wkv_projection import ProjectedWKVExtractor


MAX_REQUEST_BYTES = 2 * 1024 * 1024
MAX_BATCH_SIZE = 128


class RouterApplication:
    def __init__(
        self,
        *,
        head: Path,
        projection: Path,
        settings: LocalVLLMRWKVSettings,
    ) -> None:
        started = time.perf_counter()
        artifact = MultiHeadMLPArtifact.load(head)
        if str(artifact.metadata.get("scheme") or "") != "B":
            raise RuntimeError("persistent Router service requires the selected scheme B")
        base = PersistentVLLMRWKVExtractor(settings)
        extractor = ProjectedWKVExtractor(
            base,
            projection,
            expected_model_hash=artifact.model_hash,
            expected_projection_digest=str(
                artifact.metadata.get("projection_digest") or ""
            ),
            expected_projection_sha256=str(
                artifact.metadata.get("projection_sha256") or ""
            ),
        )
        base.load()
        self.router = StateRouter(extractor, artifact)
        self.artifact = artifact
        self.extractor = extractor
        self.started_at_unix = time.time()
        self.load_seconds = time.perf_counter() - started

    def health(self) -> dict[str, Any]:
        identity = self.extractor.identity()
        return {
            "schema_version": ROUTER_SERVICE_HEALTH_SCHEMA,
            "available": True,
            "pid": os.getpid(),
            "started_at_unix": self.started_at_unix,
            "load_seconds": self.load_seconds,
            "model_hash": self.artifact.model_hash,
            "head_hash": self.artifact.head_hash,
            "engine_revision": identity.get("engine_revision"),
            "engine_build_profile": identity.get("engine_build_profile"),
            "torch_version": identity.get("engine_torch_version"),
            "transformers_version": identity.get("engine_transformers_version"),
            "portable_identity_digest": identity.get("portable_identity_digest"),
            "feature_protocol": identity.get("feature_protocol"),
            "persistent_process": True,
        }

    def route(self, value: Mapping[str, Any]) -> dict[str, Any]:
        if value.get("schema_version") != ROUTER_SERVICE_REQUEST_SCHEMA:
            raise ValueError("unsupported State Router service request schema")
        raw_inputs = value.get("inputs")
        if not isinstance(raw_inputs, list) or not raw_inputs:
            raise ValueError("State Router service request requires inputs")
        if len(raw_inputs) > MAX_BATCH_SIZE:
            raise ValueError(f"State Router batch exceeds {MAX_BATCH_SIZE}")
        if not all(isinstance(item, Mapping) for item in raw_inputs):
            raise ValueError("State Router inputs must be objects")
        inputs = [RouterInput.from_dict(item) for item in raw_inputs]
        outputs = [item.to_dict() for item in self.router.route_many(inputs)]
        return {
            "schema_version": ROUTER_SERVICE_RESPONSE_SCHEMA,
            "outputs": outputs,
        }


class RouterHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], app: RouterApplication) -> None:
        super().__init__(address, RouterRequestHandler)
        self.app = app


class RouterRequestHandler(BaseHTTPRequestHandler):
    server: RouterHTTPServer
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: object) -> None:
        sys.stderr.write(
            "%s - - [%s] %s\n"
            % (self.address_string(), self.log_date_time_string(), format % args)
        )

    def _send(self, status: HTTPStatus, value: Mapping[str, Any]) -> None:
        payload = (
            json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n"
        ).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(payload)

    def _error(self, status: HTTPStatus, exc: Exception) -> None:
        self._send(
            status,
            {
                "error": {
                    "type": type(exc).__name__,
                    "message": str(exc)[:1000],
                }
            },
        )

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send(HTTPStatus.OK, self.server.app.health())
            return
        self._send(HTTPStatus.NOT_FOUND, {"error": {"message": "not found"}})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/route":
            self._send(HTTPStatus.NOT_FOUND, {"error": {"message": "not found"}})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length < 1 or length > MAX_REQUEST_BYTES:
                raise ValueError("invalid State Router request size")
            payload = self.rfile.read(length)
            value = json.loads(payload.decode("utf-8"))
            if not isinstance(value, Mapping):
                raise ValueError("State Router request must be an object")
            self._send(HTTPStatus.OK, self.server.app.route(value))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            self._error(HTTPStatus.BAD_REQUEST, exc)
        except Exception as exc:
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, exc)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=29620)
    parser.add_argument("--allow-non-loopback", action="store_true")
    parser.add_argument("--head", type=Path, default=DEFAULT_SHADOW_HEAD)
    parser.add_argument("--projection", type=Path, default=DEFAULT_SHADOW_PROJECTION)
    parser.add_argument("--model", type=Path, default=DEFAULT_ROUTER_MODEL)
    parser.add_argument("--engine-root", type=Path, default=DEFAULT_VLLM_RWKV_ROOT)
    parser.add_argument("--engine-python", type=Path, default=DEFAULT_VLLM_RWKV_PYTHON)
    parser.add_argument("--engine-revision", default=DEFAULT_VLLM_RWKV_REVISION)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--wkv-mode", choices=("fp16", "fp32io16"), default="fp16")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.host not in {"127.0.0.1", "::1", "localhost"} and not args.allow_non_loopback:
        raise ValueError("State Router binds loopback unless --allow-non-loopback is explicit")
    settings = LocalVLLMRWKVSettings(
        engine_root=args.engine_root,
        engine_revision=args.engine_revision,
        engine_python=args.engine_python,
        model=args.model,
        batch_size=args.batch_size,
        max_tokens=args.max_tokens,
        wkv_mode=args.wkv_mode,
    )
    app = RouterApplication(
        head=args.head.expanduser().resolve(),
        projection=args.projection.expanduser().resolve(),
        settings=settings,
    )
    server = RouterHTTPServer((args.host, args.port), app)
    print(
        json.dumps(
            {**app.health(), "listen": f"http://{args.host}:{args.port}"},
            sort_keys=True,
        ),
        flush=True,
    )
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
