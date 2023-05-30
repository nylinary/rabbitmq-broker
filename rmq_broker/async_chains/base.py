import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Union

from schema import Schema, SchemaError
from starlette import status

from rmq_broker.schemas import MessageTemplate, PostMessage, PreMessage

logger = logging.getLogger(__name__)


class AbstractChain(ABC):
    """Интерфейс классов обработчиков.

    Args:
        ABC : Вспомогательный класс, предоставляющий стандартный способ
              создания абстрактного класса.

    Attributes:
        chains (dict): {request_type:объект чейна}
    """

    chains: dict = {}

    def add(self, chain) -> None:
        """
        Добавляет нового обработчика в цепочку.
        Args:
            chain: Экземпляр обработчика.

        Returns:
            None
        """
        self.chains[chain.request_type] = chain

    @abstractmethod
    async def handle(
        self, data: dict[str, Union[str, dict[str, str]]]
    ) -> Union[Callable, None]:
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
        self, data: dict[str, Union[str, dict[str, str]]]
    ) -> dict[str, dict[str, str]]:
        """
        Изменяет заголовок запроса.

        Args:
            data (dict): Словарь с запросом.
        """
        ...  # pragma: no cover

    @abstractmethod
    async def get_response_body(
        self, data: dict[str, Union[str, dict[str, str]]]
    ) -> dict[str, Union[str, dict[str, str]]]:
        """
        Изменяет тело запроса.

        Args:
            data (dict): Словарь с запросом.

        Returns:
            Cловарь c ответом.
        """
        pass  # pragma: no cover

    @abstractmethod
    def validate(self, data: dict[str, Union[str, dict[str, str]]]) -> None:
        pass  # pragma: no cover

    def form_response(
        self,
        data: dict,
        body: Any = {},
        code: int = status.HTTP_200_OK,
        message: Union[int, str] = "",
    ) -> dict:
        data.update({"body": body})
        data.update({"status": {"message": str(message), "code": code}})
        return data


class BaseChain(AbstractChain):
    """
    Базовый классов обработчиков.

    Args:
        AbstractChain : Интерфейс классов обработчиков.

    Attributes:
        request_type (str): Тип запроса, который обработчик способен обработать.
    """

    request_type: str = ""

    async def handle(self, data):
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
        try:
            self.validate(data, PreMessage)
        except SchemaError as e:
            logger.error(f"{self.__class__.__name__}: handle(data): Error: {e}")
            return self.form_response(
                MessageTemplate, {}, status.HTTP_400_BAD_REQUEST, e
            )
        logger.debug(
            "%s: handle(data): Successful validation" % self.__class__.__name__
        )
        response = {}
        if self.request_type == data["request_type"]:
            response["request_id"] = data["request_id"]
            response["request_type"] = data["request_type"]
            logger.info("%s: get_response_body(data)" % self.__class__.__name__)
            try:
                response.update(await self.get_response_body(data))
            except Exception as e:
                return self.form_response(
                    MessageTemplate, {}, status.HTTP_400_BAD_REQUEST, e
                )
            logger.info(
                "%s: get_response_header(data) data=%s"
                % (self.__class__.__name__, data)
            )
            response.update(self.get_response_header(data))
            logger.info(f"{self.__class__.__name__}: handle(data) response={response}")
            try:
                self.validate(response, PostMessage)
                return response
            except SchemaError as e:
                logger.error(f"{self.__class__.__name__}: handle(data): Error: {e}")
                return self.form_response(
                    MessageTemplate, {}, status.HTTP_400_BAD_REQUEST, e
                )
        else:
            return self.form_response(
                MessageTemplate,
                {},
                status.HTTP_400_BAD_REQUEST,
                "Can't handle this request type",
            )

    def get_response_header(self, data):
        """
        Меняет местами получателя('dst') и отправителя('src') запроса.

        Args:
            data (dict): Словарь с запросом.

        Raises:
            ShemaError: Любой из ключей ('src', 'dst') отсутствует в словаре запроса.

        Returns:
            Словарь заголовка запроса.
        """
        return {"header": {"src": data["header"]["dst"], "dst": data["header"]["src"]}}

    def validate(
        self, data: dict[str, Union[str, dict[str, str]]], schema: Schema
    ) -> None:
        logger.debug(
            "%s.validate(data, schema): Started validation" % self.__class__.__name__
        )
        logger.debug(f"{self.__class__.__name__}.validate(data, schema): data={data}")
        logger.debug(
            "{}.validate(data, schema): schema{}".format(
                self.__class__.__name__, schema.__class__.__name__
            )
        )
        schema.validate(data)


class ChainManager(BaseChain):
    chains = {}

    def __init__(self, parent_chain=BaseChain) -> None:
        if subclasses := parent_chain.__subclasses__():
            for subclass in subclasses:
                if subclass.request_type:
                    self.chains[subclass.request_type] = subclass
                self.__init__(subclass)

    async def handle(self, data):
        if chain := self.chains.get(data["request_type"]):
            return await chain().handle(data)
        else:
            return self.form_response(
                MessageTemplate,
                {},
                status.HTTP_400_BAD_REQUEST,
                "Can't handle this request type",
            )

    async def get_response_body(self, data):
        pass
