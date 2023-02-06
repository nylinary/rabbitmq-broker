import logging
from abc import ABC, abstractmethod
from typing import Callable, Union

logger = logging.getLogger(__name__)


class AbstractChain(ABC):
    """Интерфейс классов обработчиков.

    Args:
        ABC : Вспомогательный класс, предоставляющий стандартный способ
              создания абстрактного класса.

    Attributes:
        _next_chain: Экземпляр обработчика, являющийся следующим
                     для данного обработчика.
        _last_chain: Экземпляр обработчика, являющийся последним в цепочке,
                     начинающейся с данного обработчика.
    """

    def __init__(self) -> None:
        """Создает необходимые атрибуты для объекта цепочки."""
        logger.debug("%s: initialized" % self.__class__.__name__)
        self._next_chain: AbstractChain
        self._last_chain: AbstractChain = self

    def add(self, chain) -> None:
        """
        Добавляет нового обработчика в цепочку.
        Args:
            chain: Экземпляр обработчика.

        Returns:
            None
        """
        self._last_chain._next_chain = chain
        self._last_chain = chain

    @abstractmethod
    def handle(
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
        if hasattr(self, "_next_chain"):
            return self._next_chain.handle(data)
        return None

    @abstractmethod
    def get_response_header(
        self, data: dict[str, Union[str, dict[str, str]]]
    ) -> dict[str, dict[str, str]]:
        """
        Изменяет заголовок запроса.

        Args:
            data (dict): Словарь с запросом.
        """
        pass  # pragma: no cover

    @abstractmethod
    def get_response_body(
        self, data: dict[str, Union[str, dict[str, str]]]
    ) -> dict[str, Union[str, dict[str, str]]]:
        """
        Изменяет тело запроса.

        Args:
            data (dict): Словарь с запросом.

        Returns:
            Cловарь c телом запроса.
        """
        pass  # pragma: no cover


class BaseChain(AbstractChain):
    """
    Базовый классов обработчиков.

    Args:
        AbstractChain : Интерфейс классов обработчиков.

    Attributes:
        request_type (str): Тип запроса, который обработчик способен обработать.
    """

    request_type: str = ""

    def handle(self, data):
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
        assert isinstance(data, dict)
        response = {}
        if data["request_type"] == self.request_type:
            response["request_id"] = data["request_id"]
            response["request_type"] = data["request_type"]
            logger.info("%s: get_response_body(data)" % self.__class__.__name__)
            response.update(self.get_response_body(data))
            logger.info(
                "%s: get_response_header(data) data=%s"
                % (self.__class__.__name__, data)
            )
            response.update(self.get_response_header(data))
            logger.info(f"{self.__class__.__name__}: handle(data) response={response}")
            return response
        else:
            return super().handle(data)

    def get_response_header(self, data):
        """
        Меняет местами получателя('dst') и отправителя('src') запроса.

        Args:
            data (dict): Словарь с запросом.

        Raises:
            KeyError: Любой из ключей ('src', 'dst') отсутствует в словаре запроса.
            AssertionError: Переданный аргумент

        Returns:
            Словарь заголовка запроса.
        """
        assert isinstance(data, dict)
        for item in ["dst", "src"]:
            if item not in data.get("header").keys():
                logger.exception(
                    "%s:  The %s field is missing in the message header"
                    % (self.__class__.__name__, item)
                )
                raise KeyError(f"The {item} field is missing in the message header")
        return {"header": {"src": data["header"]["dst"], "dst": data["header"]["src"]}}
