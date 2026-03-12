
from aio_pika import ExchangeType, Message, connect_robust
from aio_pika.exceptions import DeliveryError
from pamqp.commands import Basic

from core.celeryconfig import broker_url, logger


async def send_to_rabbitmq(queue_name, message, correlation_id, priority=0):
    try:
        connection = await connect_robust(broker_url)
        async with connection:
            channel = await connection.channel(publisher_confirms=True)
            exchange = await channel.declare_exchange('video-generate-service',
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
