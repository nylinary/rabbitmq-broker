import logging
from abc import abstractmethod

from pydantic.error_wrappers import ValidationError

from rmq_broker.async_chains.base import BaseChain as AsyncBaseChain
from rmq_broker.async_chains.base import ChainManager as AsyncChainManager
from rmq_broker.models import ErrorMessage, ProcessedMessage, UnprocessedMessage
from rmq_broker.schemas import ProcessedBrokerMessage, UnprocessedBrokerMessage
from rmq_broker.utils.singleton import Singleton

logger = logging.getLogger(__name__)


class BaseChain(AsyncBaseChain):
    """Синхронная версия базового класса обработчика."""

    def handle(self, data: UnprocessedBrokerMessage) -> ProcessedBrokerMessage:
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
        logger.info(
            "%s.%s: data=%s", self.__class__.__name__, self.handle.__name__, data
        )
        try:
            UnprocessedMessage(**data)
        except ValidationError as error:
            logger.error(
                "%s.%s: %s", self.__class__.__name__, self.handle.__name__, str(error)
            )
            return ErrorMessage().generate(message=str(error))
        if self.request_type.lower() == data["request_type"].lower():
            response = ProcessedMessage().generate()
            try:
                response.update(self.get_response_body(data))
                logger.debug(
                    "%s.%s: After body update response=%s",
                    self.__class__.__name__,
                    self.handle.__name__,
                    response,
                )
            except Exception as exc:
                return ErrorMessage().generate(message=str(exc))
            response.update(self.get_response_header(data))
            logger.debug(
                "%s.%s: After header update response=%s",
                self.__class__.__name__,
                self.handle.__name__,
                response,
            )
            # These field must stay the same.
            response["request_id"] = data["request_id"]
            response["request_type"] = data["request_type"]
            logger.info(
                "%s.%s: Before sending response=%s",
                self.__class__.__name__,
                self.handle.__name__,
                response,
            )
            try:
                ProcessedMessage(**response)
                return response
            except ValidationError as error:
                logger.error(
                    "%s.%s: ValidationError: %s",
                    self.__class__.__name__,
                    self.handle.__name__,
                    str(error),
                )
                return ErrorMessage().generate(message=str(error))
        else:
            logger.error(
                "%s.%s: Unknown request_type=%s",
                self.__class__.__name__,
                self.handle.__name__,
                data["request_type"],
            )
            return ErrorMessage().generate(message="Can't handle this request type")

    @abstractmethod
    def get_response_body(
        self, data: UnprocessedBrokerMessage
    ) -> ProcessedBrokerMessage:
        ...


class ChainManager(AsyncChainManager, Singleton):
    """Синхронная версия менеджера распределения запросов."""

    def handle(self, data: UnprocessedBrokerMessage) -> ProcessedBrokerMessage:
        """Направляет запрос на нужный обработчик."""
        try:
            UnprocessedMessage(**data)
            chain = self.chains[data["request_type"].lower()]
            return chain().handle(data)
        except ValidationError as error:
            msg = f"Incoming message validation error: {error}"
        except KeyError as error:
            msg = f"Can't handle this request type: {error}"
        logger.error("%s.%s: %s", self.__class__.__name__, self.handle.__name__, msg)
        return ErrorMessage().generate(message=msg)

    def get_response_body(self, data):
        pass
