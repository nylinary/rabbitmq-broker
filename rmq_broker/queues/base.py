import logging
from abc import ABC, abstractmethod

from rmq_broker.settings import settings

logger = logging.getLogger(__name__)


class AsyncAbstractMessageQueue(ABC):
    MessageQueue: str = ""

    def __init__(self):
        """Создает необходимые атрибуты для подключения к брокеру сообщений."""
        if self.MessageQueue == "":
            raise AttributeError("Broker name has not been set.")
        self.config = settings.CONSUMERS.get(self.MessageQueue)
        self.broker_url = self.config["broker_url"]
        self.connection = None
        self.client_properties = None
        logger.debug("%s: Initialized" % self.__class__.__name__)

    @abstractmethod
    async def __aenter__(self):
        pass

    @abstractmethod
    async def __aexit__(self, *args, **kwargs):
        pass

    @abstractmethod
    async def register_tasks(self, routing_key, worker):
        pass

    @abstractmethod
    async def consume(self):
        pass

    @abstractmethod
    async def post_message(self):
        pass
