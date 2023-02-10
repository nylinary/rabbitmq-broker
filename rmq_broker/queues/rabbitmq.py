from rmq_broker.queues.base import AsyncAbstractMessageQueue
import asyncio
from rmq_broker.schemas import PreMessage
from schema import SchemaError
import logging
from aio_pika.patterns import RPC
import aio_pika


logger = logging.getLogger(__name__)


class AsyncRabbitMessageQueue(AsyncAbstractMessageQueue):
    MessageQueue: str = "rabbitmq"

    async def consume(self) -> None:
        logger.info("%s.consume: RPC consumer started" % self.__class__.__name__)
        await asyncio.Future()

    async def post_message(self, data, worker):
        try:
            PreMessage.validate(data)
        except SchemaError as e:
            logger.error("%s.post_message: Message validation failed!: %s" % (self.__class__.__name__, e))
        else:
            self.rpc.call(worker, kwargs=dict(data=data))

    async def register_tasks(self, routing_key: str, worker: callable):
        """Вызывать перед стартом консьюмера."""
        self.rpc = await RPC.create(self.channel)
        await self.rpc.register(routing_key, worker, auto_delete=True)

    async def __aenter__(self):
        """
        Метод входа в контекст подключения
        """
        if self.connection is None or self.connection.is_closed:
            logger.info("%s.__aenter__: Created connection" % self.__class__.__name__)
            self.connection = await aio_pika.connect_robust(
                self.broker_url,
            )
            self.channel = await self.connection.channel()
        return self
    
    async def __aexit__(self, *args, **kwargs):
        await self.connection.close()
        await self.channel.close()
