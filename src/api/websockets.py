"""Low-overhead task status stream for clients that need live completion updates."""

from __future__ import annotations

import asyncio
import secrets

from fastapi import WebSocket, WebSocketDisconnect, status

from src.api.dependencies import get_websocket_runtime
from src.config.settings import get_settings


async def stream_task(websocket: WebSocket, task_id: str) -> None:
    api_key = websocket.headers.get("x-api-key") or websocket.query_params.get("api_key")
    if not api_key or not any(
        secrets.compare_digest(api_key, candidate) for candidate in get_settings().api_keys_list
    ):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await websocket.accept()
    runtime = get_websocket_runtime(websocket)
    previous: str | None = None
    try:
        while True:
            task = await runtime.get(task_id)
            if task is None:
                await websocket.send_json({"error": "task not found"})
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
            snapshot = task.model_dump(mode="json")
            fingerprint = str(snapshot)
            if fingerprint != previous:
                await websocket.send_json(snapshot)
                previous = fingerprint
            if task.status.is_terminal:
                await websocket.close()
                return
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        return
