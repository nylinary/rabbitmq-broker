import logging
from abc import abstractmethod

from pydantic.error_wrappers import ValidationError

from rmq_broker import models
from rmq_broker.async_chains.base import BaseChain as AsyncBaseChain
from rmq_broker.async_chains.base import ChainManager as AsyncChainManager
from rmq_broker.schemas import IncomingMessage, OutgoingMessage
from rmq_broker.utils.singleton import Singleton

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
            models.IncomingMessage(**data)
        except ValidationError as error:
            logger.error(
                f"{self.__class__.__name__}.handle(): ValidationError: {error}"
            )
            return models.ErrorMessage().generate(message=str(error))
        response = models.OutgoingMessage().generate()
        if self.request_type.lower() == data["request_type"].lower():
            try:
                response.update(self.get_response_body(data))
                logger.debug(
                    f"{self.__class__.__name__}.handle(): After body update {response=}"
                )
            except Exception as exc:
                return models.ErrorMessage().generate(message=str(exc))
            response.update(self.get_response_header(data))
            logger.debug(
                f"{self.__class__.__name__}.handle(): After header update {response=}"
            )
            # These field must stay the same.
            response["request_id"] = data["request_id"]
            response["request_type"] = data["request_type"]
            logger.debug(
                f"{self.__class__.__name__}.handle(): Before sending {response=}"
            )
            try:
                models.OutgoingMessage(**response)
                return response
            except ValidationError as error:
                logger.error(
                    f"{self.__class__.__name__}.handle(): ValidationError: {error}"
                )
                return models.ErrorMessage().generate(message=str(error))
        else:
            logger.error(
                f"{self.__class__.__name__}.handle(): Unknown request_type='{data['request_type']}'"
            )
            return models.ErrorMessage().generate(
                message="Can't handle this request type"
            )

    @abstractmethod
    def get_response_body(self, data: IncomingMessage) -> OutgoingMessage:
        ...


class ChainManager(AsyncChainManager, Singleton):
    """Синхронная версия менеджера распределения запросов."""

    def handle(self, data: IncomingMessage) -> OutgoingMessage:
        """Направляет запрос на нужный обработчик."""
        try:
            models.IncomingMessage(**data)
            chain = self.chains[data["request_type"].lower()]
            return chain().handle(data)
        except ValidationError as error:
            msg = f"Incoming message validation error: {error}"
        except KeyError as error:
            msg = f"Can't handle this request type: {error}"
        logger.error(f"{self.__class__.__name__}: handle(data): {msg}")
        return models.ErrorMessage().generate(message=msg)

    def get_response_body(self, data):
        pass
