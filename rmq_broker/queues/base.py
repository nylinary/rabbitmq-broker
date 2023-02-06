from abc import ABC, abstractmethod

from rmq_broker.settings import settings


class AbstractMessageQueue(ABC):
    MessageQueue: str = ""

    def __init__(self):
        """Создает необходимые атрибуты для подключения к брокеру сообщений."""
        if self.MessageQueue == "":
            raise AttributeError("Broker name has not been set.")
        self.config = settings.CONSUMERS.get(self.MessageQueue)
        self.host = self.config["host"]
        self.port = self.config["port"]
        self.broker_login = self.config["broker_login"]
        self.broker_pwd = self.config["broker_pwd"]

    @abstractmethod
    def post_message(self, body, queue_name):
        """Отправляет сообщение в очередь."""
        pass

    @abstractmethod
    def consume(self):
        """Включает прослушку сообщений из очереди."""
        pass

    @abstractmethod
    def callback(self):
        """
        Пропускает сообщение через фильтры и обработчики,
        после чего принимает либо отвергает его.
        """
        pass

    @abstractmethod
    def process_request(self, request, method):
        pass

    @abstractmethod
    def __enter__(self):
        pass

    @abstractmethod
    def __exit__(self, *args, **kwargs):
        pass
