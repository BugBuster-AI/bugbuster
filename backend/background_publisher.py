from config import REDIS_PREFIX, UVICORN_PORT, logger, redis_client, BROKER_URL, RABBIT_PREFIX
from db.session import async_session, transaction_scope
import asyncio
from sqlalchemy import and_, delete, func, select, update
from db.models import RunCase, GroupRunCase, Project
from schemas import CaseStatusEnum, CaseTypeEnum, RunSingleCase, CaseRead, ExecutionModeEnum
from datetime import datetime, timezone
from aio_pika import ExchangeType, Message, connect_robust
from aio_pika.exceptions import DeliveryError
from pamqp.commands import Basic


async def send_to_rabbitmq(queue_name, message, correlation_id, priority=0):
    try:
        connection = await connect_robust(BROKER_URL)
        async with connection:
            channel = await connection.channel(publisher_confirms=True)
            exchange = await channel.declare_exchange(f'{RABBIT_PREFIX}_portal-clicker',
                                                      ExchangeType.DIRECT,
                                                      durable=True)
            # queue = await channel.declare_queue(queue_name, durable=True)
            # await queue.bind(exchange, routing_key=queue_name)

            confirmation = await exchange.publish(

                Message(body=message,
                        delivery_mode=2,
                        content_type='application/json',
                        content_encoding='utf-8',
                        headers={'task': queue_name, 'id': correlation_id},
                        correlation_id=correlation_id,
                        priority=priority),
                routing_key=queue_name,
                timeout=60.0
            )
            if not isinstance(confirmation, Basic.Ack):
                if confirmation.delivery.reply_text != 'NO_ROUTE':
                    logger.error(f"confirmation PROBLEM {confirmation.delivery.reply_text} on queue_name {queue_name}")
                    raise "publish error"
    except DeliveryError as e:
        logger.error(f"Delivery of  failed with exception: {e}")
        raise e
    except TimeoutError as e:
        logger.error(f"Timeout occured for {e}")
        raise e
    except Exception as e:
        logger.error(f"publish error with {e}")
        raise e


async def monitor_task(task, timeout):
    start_time = datetime.now()

    while not task.done():
        await asyncio.sleep(timeout)
        current_time = datetime.now()
        duration = (current_time - start_time).total_seconds()
        if duration > timeout * 15 * 4:
            logger.warning(f"Publisher is running more: {duration:.2f} seconds")


async def calculate_task_and_publish_to_rabbit():
    """Для каждого workspace берем задачи в IN_QUEUE (созданная запись по клику ран), считаем сколько можно отправить
    в очередь согласно лимитам workspace, проекта и group_run_case."""
    queue_name = f'{RABBIT_PREFIX}_celery.portal-clicker.run_single_case_queue'

    async with async_session() as session:
        async with transaction_scope(session):
            # Получаем все задачи в статусах IN_QUEUE, IN_PROGRESS, PREPARATION
            tasks_query = (
                select(
                    # RunCase.run_id,
                    # RunCase.group_run_id,
                    # RunCase.status,
                    # RunCase.created_at,
                    # RunCase.current_case_version,
                    # RunCase.user_id,
                    # RunCase.workspace_id,
                    RunCase,
                    GroupRunCase.parallel_exec,
                    GroupRunCase.project_id,
                    GroupRunCase.updated_at,
                    Project.parallel_exec.label('project_parallel_exec')
                )
                .select_from(RunCase)
                .outerjoin(GroupRunCase, RunCase.group_run_id == GroupRunCase.group_run_id)
                .outerjoin(Project, GroupRunCase.project_id == Project.project_id)
                .where(RunCase.status.in_([
                    CaseStatusEnum.IN_QUEUE.value,
                    CaseStatusEnum.PREPARATION.value,
                    CaseStatusEnum.IN_PROGRESS.value]),
                    RunCase.case_type_in_run == CaseTypeEnum.AUTOMATED.value)
                .order_by(RunCase.created_at)  # (старые сначала)
            )
            tasks_result = await session.execute(tasks_query)
            tasks = tasks_result.all()

            # Получаем лимиты workspace из Redis
            workspace_ids = {task.RunCase.workspace_id for task in tasks if task.RunCase.workspace_id}
            workspace_limits = {}
            if workspace_ids:
                redis_keys = [f"{REDIS_PREFIX}_workspace_limit:{ws_id}" for ws_id in workspace_ids]
                limits = redis_client.mget(redis_keys)
                workspace_limits = {ws_id: int(limit) if limit else 0
                                    for ws_id, limit in zip(workspace_ids, limits)}

            # Структура для учета статусов и лимитов
            workspace_data = {}
            group_run_data = {}
            project_data = {}

            ACTIVE = {CaseStatusEnum.PREPARATION.value, CaseStatusEnum.IN_PROGRESS.value}

            # Сначала собираем информацию о текущих запущенных задачах
            for task in tasks:
                run_case = task.RunCase
                workspace_id = run_case.workspace_id
                group_run_id = run_case.group_run_id
                project_id = task.project_id

                # Инициализация workspace
                if workspace_id not in workspace_data:
                    workspace_data[workspace_id] = {
                        'limit': workspace_limits.get(workspace_id, 0),
                        'current_running_single': 0,
                        'current_running_group': 0,
                        'single_tasks': [],
                        # 'group_runs': set()
                    }

                # ---- GROUP RUN ----
                if group_run_id:
                    if group_run_id not in group_run_data:
                        group_run_data[group_run_id] = {
                            'parallel_exec': task.parallel_exec or 0,
                            'current_running_group': 0,   # total (seq+par)
                            'seq_active': 0,
                            'par_active': 0,
                            'project_id': project_id,
                            'workspace_id': workspace_id,
                            'updated_at': task.updated_at,
                            'seq_in_queue': [],
                            'par_in_queue': [],
                            'has_sequential_total': False,  # есть ли вообще sequential кейсы в этом запуске
                        }

                    if project_id and project_id not in project_data:
                        project_data[project_id] = {
                            'parallel_exec': task.project_parallel_exec or 0,
                            'current_running_group': 0
                        }

                    gr = group_run_data[group_run_id]

                    # помечаем что sequential вообще присутствует
                    if run_case.execution_mode == ExecutionModeEnum.sequential.value:
                        gr['has_sequential_total'] = True

                    # Учитываем задачи в процессе (занимают потоки)
                    if run_case.status in ACTIVE:
                        gr['current_running_group'] += 1
                        project_data[project_id]['current_running_group'] += 1
                        workspace_data[workspace_id]['current_running_group'] += 1

                        if run_case.execution_mode == ExecutionModeEnum.sequential.value:
                            gr['seq_active'] += 1
                        elif run_case.execution_mode == ExecutionModeEnum.parallel.value:
                            gr['par_active'] += 1

                    # Очередь
                    elif run_case.status == CaseStatusEnum.IN_QUEUE.value:
                        if run_case.execution_mode == ExecutionModeEnum.sequential.value:
                            gr['seq_in_queue'].append(run_case)
                        elif run_case.execution_mode == ExecutionModeEnum.parallel.value:
                            gr['par_in_queue'].append(run_case)

                else:
                    # Одиночные задачи (single run)
                    if run_case.status == CaseStatusEnum.IN_QUEUE.value:
                        workspace_data[workspace_id]['single_tasks'].append(run_case)
                    elif run_case.status in ACTIVE:
                        workspace_data[workspace_id]['current_running_single'] += 1

            # print("---" * 60)
            # print("workspace_data\n", workspace_data)
            # print("group_run_data\n", group_run_data)
            # print("project_data\n", project_data)

            # Обрабатываем одиночные раны (без group_run_id)
            for workspace_id, data in workspace_data.items():
                if not data['single_tasks']:
                    continue
                # последовательно, если что то выполняется, то больше не берем
                if data['current_running_single'] > 0:
                    continue

                # Берем самую старую задачу (первую в списке, т.к. сортировка по created_at)
                task_to_run = data['single_tasks'][0]

                # Отправляем задачу в RabbitMQ
                case_data = CaseRead.model_validate(task_to_run.current_case_version)
                background_video_generate = task_to_run.background_video_generate
                run_id = str(task_to_run.run_id)
                message = RunSingleCase(
                    id=run_id,
                    run_id=run_id,
                    task=queue_name,
                    args=[],
                    kwargs={
                        "run_id": run_id,
                        "user_id": str(task_to_run.user_id),
                        "case": case_data,
                        "environment": case_data.environment,
                        "background_video_generate": background_video_generate
                    }
                ).model_dump_json().encode('utf-8')

                await send_to_rabbitmq(queue_name, message, run_id)

                # Обновляем статус задачи
                await session.execute(
                    update(RunCase)
                    .where(RunCase.run_id == task_to_run.run_id)
                    .values(status=CaseStatusEnum.PREPARATION.value)
                )

            # Сортируем раны внутри groups
            BIG = 10**9

            for gr in group_run_data.values():
                # sequential: по execution_order (NULL в конец), затем по created_at/id
                gr['seq_in_queue'].sort(
                    key=lambda rc: (
                        rc.execution_order is None,
                        rc.execution_order if rc.execution_order is not None else BIG,
                        rc.created_at,
                        str(rc.run_id),
                    )
                )
                # parallel: FIFO по created_at
                gr['par_in_queue'].sort(key=lambda rc: (rc.created_at, str(rc.run_id)))

            # Сортируем GroupRunCase по updated_at (старые сначала)
            sorted_group_runs = sorted(
                group_run_data.items(),
                key=lambda x: x[1]['updated_at'] or datetime.min.replace(tzinfo=timezone.utc)  # возможные None
            )

            # Обрабатываем групповые задачи (с group_run_id)
            for group_run_id, data in sorted_group_runs:
                project_id = data['project_id']
                workspace_id = data['workspace_id']

                if workspace_id not in workspace_data:
                    continue

                # Если проект "выключен" — не запускаем вообще automated (и seq и par)
                if project_id not in project_data or project_data[project_id]['parallel_exec'] <= 0:
                    continue

                # Если нет очереди вообще — нечего делать
                if not data['seq_in_queue'] and not data['par_in_queue']:
                    continue

                # Доступные слоты с учетом всех ограничений
                available_slots = min(
                    workspace_data[workspace_id]['limit'] - workspace_data[workspace_id]['current_running_group'],
                    project_data[project_id]['parallel_exec'] - project_data[project_id]['current_running_group'],
                    data['parallel_exec'] - data['current_running_group']
                )
                # print("available_slots", group_run_id, available_slots)
                if available_slots <= 0:
                    continue

                # -------- Определяем фазу по факту --------
                sequential_phase = (
                    data['has_sequential_total'] and
                    (data['seq_active'] > 0 or len(data['seq_in_queue']) > 0)
                )

                # ======== SEQUENTIAL PHASE ========
                if sequential_phase:
                    # sequential занимает максимум 1 поток на group_run:
                    # запускаем следующий только если сейчас sequential ничего не выполняет
                    if data['seq_active'] > 0:
                        # уже есть sequential в работе — ничего не отправляем
                        continue

                    if not data['seq_in_queue']:
                        # sequential "по факту" закончился (нет очереди), дадим перейти к parallel в этой же итерации
                        pass
                    else:
                        # берем ровно 1 задачу
                        task_to_run = data['seq_in_queue'][0]

                        case_data = CaseRead.model_validate(task_to_run.current_case_version)
                        background_video_generate = task_to_run.background_video_generate
                        run_id = str(task_to_run.run_id)

                        message = RunSingleCase(
                            id=run_id,
                            run_id=run_id,
                            task=queue_name,
                            args=[],
                            kwargs={
                                "run_id": run_id,
                                "user_id": str(task_to_run.user_id),
                                "case": case_data,
                                "group_run_id": str(group_run_id),
                                "environment": case_data.environment,
                                "background_video_generate": background_video_generate
                            }
                        ).model_dump_json().encode('utf-8')

                        await send_to_rabbitmq(queue_name, message, run_id)

                        await session.execute(
                            update(RunCase)
                            .where(RunCase.run_id == task_to_run.run_id)
                            .values(status=CaseStatusEnum.PREPARATION.value)
                        )

                        # выставляем фазу на уровне GroupRunCase (витрина для UI)
                        await session.execute(
                            update(GroupRunCase)
                            .where(GroupRunCase.group_run_id == group_run_id)
                            .values(current_phase=ExecutionModeEnum.sequential.value,
                                    parallel_started_at=None)
                        )

                        # счетчики (заняли 1 поток)
                        data['current_running_group'] += 1
                        data['seq_active'] += 1
                        project_data[project_id]['current_running_group'] += 1
                        workspace_data[workspace_id]['current_running_group'] += 1

                        continue  # sequential фазу параллельными не смешиваем

                # ======== PARALLEL PHASE ========
                if not data['par_in_queue']:
                    continue

                # Берем максимально возможное
                tasks_to_run = data['par_in_queue'][:available_slots]
                if not tasks_to_run:
                    continue

                # если переходим в parallel — фиксируем момент начала parallel
                # (делаем один апдейт на GR, а не на каждый кейс)
                await session.execute(
                    update(GroupRunCase)
                    .where(GroupRunCase.group_run_id == group_run_id)
                    .values(
                        current_phase=ExecutionModeEnum.parallel.value,
                        parallel_started_at=func.coalesce(GroupRunCase.parallel_started_at, datetime.now(timezone.utc))
                    )
                )

                for task_to_run in tasks_to_run:
                    case_data = CaseRead.model_validate(task_to_run.current_case_version)
                    background_video_generate = task_to_run.background_video_generate
                    run_id = str(task_to_run.run_id)

                    message = RunSingleCase(
                        id=run_id,
                        run_id=run_id,
                        task=queue_name,
                        args=[],
                        kwargs={
                            "run_id": run_id,
                            "user_id": str(task_to_run.user_id),
                            "case": case_data,
                            "group_run_id": str(group_run_id),
                            "environment": case_data.environment,
                            "background_video_generate": background_video_generate
                        }
                    ).model_dump_json().encode('utf-8')

                    await send_to_rabbitmq(queue_name, message, run_id)

                    await session.execute(
                        update(RunCase)
                        .where(RunCase.run_id == task_to_run.run_id)
                        .values(status=CaseStatusEnum.PREPARATION.value)
                    )

                    # счетчики
                    data['current_running_group'] += 1
                    data['par_active'] += 1
                    project_data[project_id]['current_running_group'] += 1
                    workspace_data[workspace_id]['current_running_group'] += 1


async def publisher():
    logger.info('Starting publisher')
    while True:
        try:
            task = asyncio.create_task(calculate_task_and_publish_to_rabbit())
            monitor = asyncio.create_task(monitor_task(task, 1))

            await task
            if not task.cancelled():
                await monitor

            # logger.info("Publish completed successfully.")

        except Exception as e:
            logger.error(f"Global error in publisher: {e}", exc_info=True)

        # Задержка перед повторным запуском
        await asyncio.sleep(2)  # можно 1 попробовать
