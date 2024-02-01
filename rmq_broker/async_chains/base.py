import logging
from abc import ABC, abstractmethod

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
    """Интерфейс классов обработчиков.

    Args:
        ABC : Вспомогательный класс, предоставляющий стандартный способ
              создания абстрактного класса.

    Arguments:
        chains (dict): {request_type:объект чейна}
    """

    chains: dict = {}

    def add(self, chain: object) -> None:
        """
        Добавляет нового обработчика в цепочку.
        Args:
            chain: Экземпляр обработчика.

        Returns:
            None
        """
        self.chains[chain.request_type.lower()] = chain
        logger.debug(
            f"{self.__class__.__name__}.add(): {chain.__name__} added to chains."
        )

    @abstractmethod
    async def handle(self, data: UnprocessedBrokerMessage) -> ProcessedBrokerMessage:
        """
        Вызывает метод handle() у следующего обработчика в цепочке.

        Args:
            data (dict): Словарь с запросом.

        Returns:
            None: если следующий обработчик не определен.
            Обработанный запрос: если следующий обработчик определен.
        """
        ...

    @abstractmethod
    def get_response_header(
        self, data: UnprocessedBrokerMessage
    ) -> BrokerMessageHeader:
        """
        Изменяет заголовок запроса.

        Args:
            data (dict): Словарь с запросом.
        """
        ...  # pragma: no cover

    @abstractmethod
    async def get_response_body(
        self, data: UnprocessedBrokerMessage
    ) -> ProcessedBrokerMessage:
        """
        Изменяет тело запроса.

        Args:
            data (dict): Словарь с запросом.

        Returns:
            Cловарь c ответом.
        """
        ...  # pragma: no cover

    def form_response(
        self,
        data: UnprocessedBrokerMessage,
        body: dict = None,
        code: int = status.HTTP_200_OK,
        message: str = "",
    ) -> ProcessedBrokerMessage:
        body = {} if body is None else body
        data.update({"body": body})
        data.update({"status": {"message": str(message), "code": code}})
        logger.debug(
            f"{self.__class__.__name__}.form_response(): Formed response {data=}"
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
        logger.info(f"{self.__class__.__name__}.get_response_body(): data={data}")
        try:
            UnprocessedMessage(**data)
        except ValidationError as error:
            logger.error(f"{self.__class__.__name__}.handle(): {error}")
            return ErrorMessage().generate(message=str(error))
        if self.request_type.lower() == data["request_type"].lower():
            response = ProcessedMessage().generate()
            try:
                response.update(await self.get_response_body(data))
                logger.debug(
                    f"{self.__class__.__name__}.handle(): After body update {response=}"
                )
            except Exception as exc:
                return ErrorMessage().generate(message=str(exc))
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
                ProcessedMessage(**response)
                return response
            except ValidationError as error:
                logger.error(
                    f"{self.__class__.__name__}.handle(): ValidationError: {error}"
                )
                return ErrorMessage().generate(message=str(error))
        else:
            logger.error(
                f"{self.__class__.__name__}.handle(): Unknown request_type='{data['request_type']}'"
            )
            return ErrorMessage().generate(message="Can't handle this request type")

    def get_response_header(
        self, data: UnprocessedBrokerMessage
    ) -> BrokerMessageHeader:
        """
        Меняет местами получателя('dst') и отправителя('src') запроса.

        Args:
            data (dict): Словарь с запросом.

        Returns:
            Словарь заголовка запроса.
        """
        updated_header = {
            "header": {"src": data["header"]["dst"], "dst": data["header"]["src"]}
        }
        logger.debug(
            f"{self.__class__.__name__}.get_response_header(): {updated_header=}"
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
        logger.error(f"{self.__class__.__name__}.handle(): {msg}")
        return ErrorMessage().generate(message=msg)

    async def get_response_body(self, data):
        pass
