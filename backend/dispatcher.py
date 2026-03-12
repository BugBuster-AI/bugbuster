from fastapi import WebSocket
from pydantic import ValidationError

from config import logger
from connections import ConnectionManager
from schemas import Task, UserRead
from workers.save_happy_pass import handle_save_happy_pass


async def dispatcher(manager: ConnectionManager, ws: WebSocket, task_data: dict, current_user: UserRead):
    try:
        task = Task(**task_data)
        # logger.info(f"Receive: {task} from user_id: {current_user.user_id}")

        if task.type == 'admin':
            pass
            # await admin_func(manager, task, ws)
        elif task.type == 'save_happy_pass':
            await handle_save_happy_pass(manager, task, current_user, ws)
        else:
            raise ValueError("Invalid message format, unexpected type")

    except ValidationError as e:
        err = {"type": task_data.get('type'), "state": "error", "message": f"Wrong command: {str(e)}"}
        await manager.send_personal_message(err, ws)
    except Exception as e:
        err = {"type": task_data.get('type'), "state": "error", "message": f"error: {str(e)}"}
        logger.error(err, exc_info=True)
        await manager.send_personal_message(err, ws)
