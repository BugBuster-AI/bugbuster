import json
import uuid
from json import JSONDecodeError

from fastapi import WebSocket
from fastapi.websockets import WebSocketState

from core.config import logger


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[uuid: WebSocket] = {}
        self.stop_tasks: set[str] = set()
        self.task_to_clients: dict[str, list[str]] = {}  # task_id -> [client UUIDs]

        self.received_chunks: dict[str, list[str]] = {}

        self.chatgpt_connections = {}
        self.history = {}

    def add_task_for_client(self, task_id: str, client_id: str):
        if task_id not in self.task_to_clients:
            self.task_to_clients[task_id] = []
        self.task_to_clients[task_id].append(client_id)

    def remove_task_for_client(self, task_id: str, client_id: str):
        if task_id in self.task_to_clients:
            self.task_to_clients[task_id].remove(client_id)
            if not self.task_to_clients[task_id]:
                del self.task_to_clients[task_id]

    def get_tasks_for_client(self, client_id: str) -> list[str]:
        associated_tasks = []
        for task_id, clients in self.task_to_clients.items():
            if client_id in clients:
                associated_tasks.append(task_id)
        return associated_tasks

    async def broadcast_clients_of_task(self, task_id: str, message: dict):
        if task_id in self.task_to_clients:
            for client_id in self.task_to_clients[task_id]:
                websocket = self.active_connections.get(client_id)
                if websocket:
                    await self.send_personal_message(message, websocket)

    def set_stop_flag(self, task_id: str):
        logger.info(f"stop_tasks add {task_id}")
        self.stop_tasks.add(task_id)

    def clear_stop_flag(self, task_id: str):
        self.stop_tasks.discard(task_id)

    def should_stop(self, task_id: str) -> bool:
        return task_id in self.stop_tasks

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

    def get_chatgpt_conn_list(self):
        return list(self.chatgpt_connections.keys())

    def get_chatgpt_conn_cnt(self):
        return len(list(self.chatgpt_connections.keys()))

    def get_chatgpt_current_conn(self, id):
        chatgpt_connections = self.chatgpt_connections.copy()
        return chatgpt_connections.get(id)

    def add_chagpt_conn(self, id, obj):
        self.chatgpt_connections.update({id: obj})

    def add_history(self, id, obj):
        self.history.update({id: obj})

    def get_history_current_conn(self, id):
        return self.history.get(id)

    async def kill_session(self, id: uuid):
        """убить сессию"""
        if id in self.active_connections:
            await self.disconnect(id)
            return f"kill session {id=}"
        return f"Session {id=} not found"

    async def disconnect(self, id: uuid):
        """отсоединяем клиента, очищаем
        сохраненные коннекты к моделям"""
        websocket: WebSocket = self.active_connections.pop(id, None)
        self.chatgpt_connections.pop(id, None)
        self.history.pop(id, None)

        if websocket:
            if websocket.client_state != WebSocketState.DISCONNECTED:
                await websocket.close()

    async def disconnect_not_authorized(self, websocket: WebSocket, er: dict):
        """отсоединяем неавторизованных"""

        mess = json.dumps({"type": "connect", "state": "error", "message": er}, ensure_ascii=False)
        if websocket:
            if websocket.client_state != WebSocketState.DISCONNECTED:
                await websocket.close(code=1008, reason=mess)
                logger.info(mess)

    async def connect(self, id: uuid, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.update({id: websocket})
        # mess = {"type": "connect", "state": "authorized", "message": str(id)}
        # await self.send_personal_message(mess, websocket)

    async def send_personal_message(self, message, websocket: WebSocket):
        """отправка мессаджа на web, слать json-пригодное"""
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                message = json.dumps(message, ensure_ascii=False, default=str)
                await websocket.send_text(message)
                logger.info(f"send_personal_message to portal: {message}")
            except JSONDecodeError:
                logger.error(f"You want send_personal_message to portal, but error: {message}", exc_info=True)

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
