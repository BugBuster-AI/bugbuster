import asyncio
import json
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from config import logger
from connections import ConnectionManager
from db.models import User
from dependencies.roles import get_current_active_user_with_roles_ws
from dispatcher import dispatcher

manager = ConnectionManager()
router = APIRouter(prefix="/api", tags=["ws"])


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):

    await ws.accept()

    try:

        # Получить токен из первого сообщения
        status = False
        current_user = None
        data = await ws.receive_text()
        token_data = json.loads(data)
        token = token_data.get("token")
        client_type = token_data.get("type", None)
        if not token:
            await manager.disconnect_not_authorized(ws, {"detail": "Not found token"})
            return

        ok, current_user = await get_current_active_user_with_roles_ws(token, client_type)

        if not ok:
            await manager.disconnect_not_authorized(ws, current_user)
            return

        session_id = str(uuid.uuid4())
        await manager.connect(current_user.user_id, session_id, ws, client_type)

        while True:
            logger.info("Waiting for data")
            data = await ws.receive()

            logger.info(f"Received data from user: {current_user.user_id} | session: {session_id} | ip: {ws.client.host}")
            if 'text' in data:
                task_data = json.loads(data['text'])

                asyncio.create_task(dispatcher(manager, ws, task_data, current_user))
            else:
                await manager.send_personal_message({"type": "error", "state": "error",
                                                     "message": f"Json expected, you sent: {data}"}, ws)

    except json.JSONDecodeError:
        err = {"status": "error", "type": "error", "state": "error", "message": "No valid Json"}
        await manager.send_personal_message(err, ws)

    except (WebSocketDisconnect, RuntimeError):
        await manager.disconnect(session_id)

    except Exception as e:
        await manager.send_personal_message({"status": "error", "type": "error", "message": f"Server error: {e}"}, ws)
        await manager.disconnect(session_id)

    finally:
        if status and isinstance(current_user, User):
            await manager.disconnect(session_id)
