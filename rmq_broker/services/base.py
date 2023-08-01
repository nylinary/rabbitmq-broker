import asyncio
import logging

import aio_pika
from aio_pika.patterns import RPC
from pydantic.error_wrappers import ValidationError

from rmq_broker.models import ErrorMessage, ProcessedMessage, UnprocessedMessage
from rmq_broker.schemas import ProcessedBrokerMessage, UnprocessedBrokerMessage
from rmq_broker.settings import settings

logger = logging.getLogger(__name__)


class BaseService:
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

    async def send_message(
        self, request_type: str, body: dict
    ) -> ProcessedBrokerMessage:
        """Генерирует уникальный id запроса и вызывает отправку сформированного
        сообщения.
        """
        message = UnprocessedMessage().generate(
            request_type=request_type,
            src=self.service_name,
            dst=self.dst_service_name,
            body=body,
        )
        return await self.send_rpc_request(message)

    async def send_rpc_request(
        self, message: UnprocessedBrokerMessage
    ) -> ProcessedBrokerMessage:
        """Валидирует сообщение, создает соединение с брокером и отправляет
        сообщение в очередь.
        В случае ошибки формирует сообщение с данными об ошибке и HTTP кодом 400.
        """
        try:
            UnprocessedMessage(**message)
        except ValidationError as error:
            logger.error(
                "{}.post_message: UnprocessedMessage validation failed!: {}".format(
                    self.__class__.__name__, error
                )
            )
            return ErrorMessage().generate(message=str(error))
        try:
            connection = await aio_pika.connect_robust(self.broker_url)
            async with connection, connection.channel() as channel:
                rpc = await RPC.create(channel)
                response = await rpc.call(
                    self.dst_service_name, kwargs=dict(data=message)
                )
                ProcessedMessage(**response)
                return response
        except (
            asyncio.TimeoutError,
            asyncio.CancelledError,
            RuntimeError,
            ValidationError,
        ) as err:
            return ErrorMessage().generate(
                request_id=message["request_id"],
                request_type=message["request_type"],
                src=self.dst_service_name,
                dst=self.service_name,
                message=str(err),
            )
