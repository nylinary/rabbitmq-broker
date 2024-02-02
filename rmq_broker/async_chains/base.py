import logging
from abc import ABC, abstractmethod
from typing import Dict

from pydantic.error_wrappers import ValidationError
from starlette import status

from rmq_broker.models import ErrorMessage, ProcessedMessage, UnprocessedMessage
from rmq_broker.schemas import (
    BrokerMessageHeader,
    ProcessedBrokerMessage,
    UnprocessedBrokerMessage,
)
from rmq_broker.utils.singleton import Singleton

logger = logging.getLogger(__name__)


class AbstractChain(ABC):
    chains: Dict[str, "BaseChain"] = {}

    def add(self, chain: "BaseChain") -> None:
        """Добавляет нового обработчика в цепочку."""
        self.chains[chain.request_type.lower()] = chain
        logger.debug(
            "%s.%s: %s added to chains.",
            self.__class__.__name__,
            self.add.__name__,
            chain.__name__,
        )

    @abstractmethod
    async def handle(self, data: UnprocessedBrokerMessage) -> ProcessedBrokerMessage:
        ...

    @abstractmethod
    def get_response_header(
        self, data: UnprocessedBrokerMessage
    ) -> BrokerMessageHeader:
        ...  # pragma: no cover

    @abstractmethod
    async def get_response_body(
        self, data: UnprocessedBrokerMessage
    ) -> ProcessedBrokerMessage:
        ...  # pragma: no cover

    def form_response(
        self,
        data: UnprocessedBrokerMessage,
        body: dict = None,
        code: int = status.HTTP_200_OK,
        message: str = "",
    ) -> ProcessedBrokerMessage:
        body = body or {}
        data.update({"body": body})
        data.update({"status": {"message": str(message), "code": code}})
        logger.debug(
            "%s.%s: Formed response data=%s",
            self.__class__.__name__,
            self.form_response.__name__,
            data,
        )
        return data


class BaseChain(AbstractChain):
    """
    Базовый классов обработчиков.

    Args:
        AbstractChain: Интерфейс классов обработчиков.

    Attributes:
        request_type (str): Тип запроса, который обработчик способен обработать.
        include_in_schema (bool): True (значение по умолчанию) - выводить Chain в Swagger документацию;
                                False - исключить Chain из Swagger документации.
        deprecated (bool): False (значение по умолчанию) - Chain актуален;
                        True - отметить Chain, как устаревший.
        actual (str): Наименование актуального Chain в Swagger документации. Отображается
                    рядом с устаревшим Chain (где include_in_schema = True, deprecated = True).
                    Устанавливает deprecated = True автоматически, если deprecated не был указан как True.
    """

    request_type: str = ""
    include_in_schema: bool = True
    deprecated: bool = False
    actual: str = ""

    async def handle(self, data: UnprocessedBrokerMessage) -> ProcessedBrokerMessage:
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
                response.update(await self.get_response_body(data))
                logger.debug(
                    "%s.%s: After body update response=%s",
                    self.handle.__name__,
                    self.__class__.__name__,
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

    def get_response_header(
        self, data: UnprocessedBrokerMessage
    ) -> BrokerMessageHeader:
        """Меняет местами получателя('dst') и отправителя('src') запроса."""
        updated_header = {
            "header": {"src": data["header"]["dst"], "dst": data["header"]["src"]}
        }
        logger.debug(
            "%s.%s: updated_header=%s",
            self.__class__.__name__,
            self.get_response_header.__name__,
            updated_header,
        )
        return updated_header


class ChainManager(BaseChain, Singleton):
    """Единая точка для распределения запросов по обработчикам."""

    chains = {}

    def __init__(self, parent_chain: BaseChain = BaseChain) -> None:
        """Собирает все обработчики в словарь."""
        if subclasses := parent_chain.__subclasses__():
            for subclass in subclasses:
                if subclass.request_type:
                    self.add(subclass)
                self.__init__(subclass)

    async def handle(self, data: UnprocessedBrokerMessage) -> ProcessedBrokerMessage:
        """Направляет запрос на нужный обработчик."""
        try:
            UnprocessedMessage(**data)
            chain = self.chains[data["request_type"].lower()]
            return await chain().handle(data)
        except ValidationError as error:
            msg = f"Incoming message validation error: {error}"
        except KeyError as error:
            msg = f"Can't handle this request type: {error}"
        logger.error("%s.%s: %s", self.__class__.__name__, self.handle.__name__, msg)
        return ErrorMessage().generate(message=msg)

    async def get_response_body(self, data):
        pass
