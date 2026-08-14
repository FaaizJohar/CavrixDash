from __future__ import annotations

import json

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import UnauthorizedError
from app.core.security import decode_token
from app.models.server import UserServer
from app.models.user import User
from app.services import pterodactyl_service as panel
from app.services import server_service

router = APIRouter()


@router.websocket("/ws/console/{server_id}")
async def console_ws(websocket: WebSocket, server_id: str):
    await websocket.accept()
    token = websocket.query_params.get("token", "")
    if not token:
        await websocket.close(code=4001)
        return

    db: Session = next(get_db())
    try:
        try:
            payload = decode_token(token)
        except Exception:
            await websocket.close(code=4001)
            return
        if payload.get("type") != "access":
            await websocket.close(code=4001)
            return
        user = db.query(User).filter(User.id == payload["sub"]).first()
        if not user:
            await websocket.close(code=4001)
            return
        server = db.query(UserServer).filter(UserServer.id == server_id).first()
        if not server or (server.user_id != user.id and not user.is_admin):
            await websocket.close(code=4003)
            return

        # Proxy mode: forward commands to Pterodactyl websocket.
        client = panel.get_client(db)
        ws_info = client.websocket(panel.server_identifier(server))
        await websocket.send_json({"type": "status", "state": "connected"})

        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except Exception:
                msg = {"type": "command", "command": data}
            if msg.get("type") == "command":
                cmd = msg.get("command", "")
                try:
                    client.send_command(panel.server_identifier(server), cmd)
                except Exception as exc:
                    await websocket.send_json({"type": "error", "message": str(exc)})
            elif msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
    finally:
        db.close()
