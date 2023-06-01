import logging
from abc import abstractmethod

from schema import SchemaError
from starlette import status

from rmq_broker.async_chains.base import BaseChain as AsyncBaseChain
from rmq_broker.async_chains.base import ChainManager as AsyncChainManager
from rmq_broker.schemas import (
    IncomingMessage,
    MessageTemplate,
    OutgoingMessage,
    PostMessage,
    PreMessage,
)

logger = logging.getLogger(__name__)


class BaseChain(AsyncBaseChain):
    """Синхронная версия базового класса обработчика."""

    def handle(self, data: IncomingMessage) -> OutgoingMessage:
        """
        Обрабатывает запрос, пропуская его через методы обработки
        заголовка и тела запроса.

        Args:
            data (dict): Словарь с запросом.

        Returns:
            Обработанный запрос: если типы запроса переданного сообщения
            и конкретного экземпляра обработчика совпадают.

            Метод handle() у родительского класса: если типы запроса переданного сообщения
            и конкретного экземпляра обработчика отличаются.
        """
        logger.info(f"{self.__class__.__name__}.get_response_body(): data={data}")
        try:
            self.validate(data, PreMessage)
        except SchemaError as e:
            logger.error(f"{self.__class__.__name__}.handle(): SchemaError: {e}")
            return self.form_response(
                MessageTemplate, {}, status.HTTP_400_BAD_REQUEST, e
            )
        response = {}
        if self.request_type.lower() == data["request_type"].lower():
            response["request_id"] = data["request_id"]
            response["request_type"] = data["request_type"]
            try:
                response.update(self.get_response_body(data))
                logger.debug(
                    f"{self.__class__.__name__}.handle(): After body update {response=}"
                )
            except Exception as e:
                return self.form_response(
                    MessageTemplate, {}, status.HTTP_400_BAD_REQUEST, e
                )
            response.update(self.get_response_header(data))
            logger.debug(
                f"{self.__class__.__name__}.handle(): After header update {response=}"
            )
            try:
                self.validate(response, PostMessage)
                return response
            except SchemaError as e:
                logger.error(f"{self.__class__.__name__}.handle(): SchemaError: {e}")
                return self.form_response(
                    MessageTemplate, {}, status.HTTP_400_BAD_REQUEST, e
                )
        else:
            logger.error(
                f"{self.__class__.__name__}.handle(): Unknown request_type='{data['request_type']}'"
            )
            return self.form_response(
                MessageTemplate,
                {},
                status.HTTP_400_BAD_REQUEST,
                "Can't handle this request type",
            )

    @abstractmethod
    def get_response_body(self, data: IncomingMessage) -> OutgoingMessage:
        ...


class ChainManager(AsyncChainManager):
    """Синхронная версия менеджера распределения запросов."""

    def handle(self, data: IncomingMessage) -> OutgoingMessage:
        """Направляет запрос на нужный обработчик."""
        try:
            self.validate(data, PreMessage)
            chain = self.chains[data["request_type"].lower()]
            return chain().handle(data)
        except SchemaError as e:
            msg = f"Incoming message validation error: {e}"
        except KeyError as e:
            msg = f"Can't handle this request type: {e}"
        logger.error(f"{self.__class__.__name__}: handle(data): {msg}")
        return self.form_response(
            MessageTemplate,
            {},
            status.HTTP_400_BAD_REQUEST,
            msg,
        )

    def get_response_body(self, data):
        pass
