import json
import uuid
from json import JSONDecodeError

import websockets
from fastapi import WebSocket
from fastapi.websockets import WebSocketState
from config import logger


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[uuid: WebSocket] = {}
        self.received_chunks: dict[str, list[str]] = {}

    def get_chunks_for_task(self, task_id: str) -> list[str]:
        return self.received_chunks.get(task_id, [])

    def append_chunk_for_task(self, task_id: str, chunk: str):
        if task_id not in self.received_chunks:
            self.received_chunks[task_id] = []
        self.received_chunks[task_id].append(chunk)

    def delete_chunks_for_task(self, task_id: str):
        if task_id in self.received_chunks:
            del self.received_chunks[task_id]

    def get_conn_list(self):
        return list(self.active_connections.keys())

    async def kill_session(self, id: uuid):
        """убить сессию"""
        if id in self.active_connections:
            await self.disconnect(id)
            return f"kill session {id=}"
        return f"Session {id=} not found"

    async def disconnect(self, id: uuid):
        """отсоединяем сессию"""
        websocket: WebSocket = self.active_connections.pop(id, None)

        if websocket:
            if websocket.client_state != WebSocketState.DISCONNECTED:
                await websocket.close()

    async def disconnect_not_authorized(self, websocket: WebSocket, er: dict):
        """отсоединяем неавторизованных"""

        mess = json.dumps({"type": "connect", "state": "error", "status": "error", "message": er}, ensure_ascii=False)
        if websocket:
            if websocket.client_state != WebSocketState.DISCONNECTED:
                await websocket.close(code=1008, reason=mess[:123])
                logger.info(mess)

    async def connect(self, user_id: uuid, session_id: uuid, websocket: WebSocket, client_type: str = None):
        # await websocket.accept()
        self.active_connections.update({session_id: websocket})
        mess = {"type": "connect", "state": "authorized", "status": "success",
                "client_type": client_type, "message": f"{user_id=} | {session_id=}"}
        await self.send_personal_message(mess, websocket)

    async def send_personal_message(self, message, websocket: WebSocket):
        """отправка мессаджа на web, слать json-пригодное"""
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                message = json.dumps(message, ensure_ascii=False, default=str)
                await websocket.send_text(message)
                logger.info(f"send_personal_message to portal: {message}")
            except JSONDecodeError:
                logger.error(f"You want send_personal_message to portal, but error: {message}", exc_info=True)
            except Exception as e:
                logger.error(f"Unexpected error while sending message: {message} — {e}")

    async def broadcast(self, message):
        """отправка мессаджа всем клиентам"""
        logger.info(f"broadcast active clients: {len(self.active_connections)}")
        try:
            message = json.dumps(message, ensure_ascii=False)
            for connection in self.active_connections.values():
                try:
                    await connection.send_text(message)
                except Exception as er:
                    logger.error(f"broadcast to client: {connection} {message=} with error {er}", exc_info=True)
        except JSONDecodeError:
            logger.error(f"You want send_personal_message to portal, but error: {message}", exc_info=True)
