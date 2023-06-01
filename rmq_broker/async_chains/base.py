import logging
from abc import ABC, abstractmethod

from schema import Schema, SchemaError
from starlette import status

from rmq_broker.schemas import (
    IncomingMessage,
    MessageHeader,
    MessageTemplate,
    OutgoingMessage,
    PostMessage,
    PreMessage,
)

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
    async def handle(self, data: IncomingMessage) -> OutgoingMessage:
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
    def get_response_header(self, data: IncomingMessage) -> MessageHeader:
        """
        Изменяет заголовок запроса.

        Args:
            data (dict): Словарь с запросом.
        """
        ...  # pragma: no cover

    @abstractmethod
    async def get_response_body(self, data: IncomingMessage) -> OutgoingMessage:
        """
        Изменяет тело запроса.

        Args:
            data (dict): Словарь с запросом.

        Returns:
            Cловарь c ответом.
        """
        ...  # pragma: no cover

    @abstractmethod
    def validate(self, data: IncomingMessage) -> None:
        ...  # pragma: no cover

    def form_response(
        self,
        data: IncomingMessage,
        body: dict = None,
        code: int = status.HTTP_200_OK,
        message: str = "",
    ) -> OutgoingMessage:
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
    """

    request_type: str = ""

    async def handle(self, data: IncomingMessage) -> OutgoingMessage:
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
        if self.request_type == data["request_type"]:
            response["request_id"] = data["request_id"]
            response["request_type"] = data["request_type"]
            try:
                response.update(await self.get_response_body(data))
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

    def get_response_header(self, data: IncomingMessage) -> MessageHeader:
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

    def validate(self, message: IncomingMessage, schema: Schema) -> None:
        """Валидирует сообщение по переданной схеме.

        Raises:
            SchemaError: Валидация не была пройдена.
        """
        schema.validate(message)
        logger.debug(
            f"{self.__class__.__name__}.validate(): Successful validation, {message=}"
        )


class ChainManager(BaseChain):
    """Единая точка для распределения запросов по обработчикам."""

    chains = {}

    def __init__(self, parent_chain: BaseChain = BaseChain) -> None:
        """Собирает все обработчики в словарь."""
        if subclasses := parent_chain.__subclasses__():
            for subclass in subclasses:
                if subclass.request_type:
                    self.add(subclass)
                self.__init__(subclass)

    async def handle(self, data: IncomingMessage) -> OutgoingMessage:
        """Направляет запрос на нужный обработчик."""
        try:
            self.validate(data, PreMessage)
            chain = self.chains[data["request_type"].lower()]
            return await chain().handle(data)
        except SchemaError as e:
            msg = f"Incoming message validation error: {e}"
        except KeyError as e:
            msg = f"Can't handle this request type: {e}"
        logger.error(f"{self.__class__.__name__}.handle(): {msg}")
        return self.form_response(
            MessageTemplate,
            {},
            status.HTTP_400_BAD_REQUEST,
            msg,
        )

    async def get_response_body(self, data):
        pass
