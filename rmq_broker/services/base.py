import asyncio
import logging
from abc import ABC, abstractmethod
from uuid import uuid4

import aio_pika
from aio_pika.patterns import RPC
from schema import SchemaError

from rmq_broker.schemas import IncomingMessage, OutgoingMessage, PreMessage
from rmq_broker.settings import settings
from rmq_broker.utils.message_generation import Message

logger = logging.getLogger(__name__)


class AbstractService(ABC):
    """Отправка сообщений в сервисы."""

    broker_name: str = ""
    dst_service_name: str = ""

    @abstractmethod
    async def send_message(
        self, request_type: str, body: IncomingMessage
    ) -> OutgoingMessage:
        ...

    @abstractmethod
    async def send_rpc_request(self, message: IncomingMessage) -> OutgoingMessage:
        ...


class BaseService(AbstractService):
    """Отправка сообщений в сервисы."""

    broker_name = "rabbitmq"
    config = settings.CONSUMERS.get(broker_name)
    broker_url = config["broker_url"]
    service_name = settings.SERVICE_NAME

    def __init__(self):
        """Создает необходимые атрибуты для подключения к брокеру сообщений."""
        if not self.dst_service_name:
            raise AttributeError(
                f"Attribute `dst_service_name` has not been set for class {self.__class__.__name__}"
            )

    async def send_message(self, request_type: str, body: dict) -> OutgoingMessage:
        """Генерирует уникальный id запроса и вызывает отправку сформированного
        сообщения.
        """
        request_id = uuid4().hex
        return await self.send_rpc_request(
            Message.make_request_msg(
                request_type,
                body,
                self.service_name,
                self.dst_service_name,
                request_id=request_id,
            )
        )

    async def send_rpc_request(self, message: OutgoingMessage) -> IncomingMessage:
        """Валидирует сообщение, создает соединение с брокером и отправляет
        сообщение в очередь.
        В случае ошибки формирует сообщение с данными об ошибке и HTTP кодом 500.
        """
        try:
            PreMessage.validate(message)
        except SchemaError as e:
            logger.error(
                "{}.post_message: Message validation failed!: {}".format(
                    self.__class__.__name__, e
                )
            )
        try:
            connection = await aio_pika.connect_robust(self.broker_url)
            async with connection, connection.channel() as channel:
                rpc = await RPC.create(channel)
                return await rpc.call(self.dst_service_name, kwargs=dict(data=message))
        except (asyncio.TimeoutError, asyncio.CancelledError, RuntimeError) as err:
            return Message.make_error_msg(
                message["request_id"],
                message["request_type"],
                self.service_name,
                self.dst_service_name,
                str(err),
            )
