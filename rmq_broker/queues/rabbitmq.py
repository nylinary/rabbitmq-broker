import json
import logging
from json.decoder import JSONDecodeError

import pika
from pika.exceptions import ChannelWrongStateError
from schema import SchemaError

from rmq_broker.queues.base import AbstractMessageQueue
from rmq_broker.schemas import PreMessage

logger = logging.getLogger(__name__)


class RabbitMessageQueue(AbstractMessageQueue):
    MessageQueue: str = "rabbitmq"

    def __init__(self):
        super().__init__()
        self.queue_name = self.config.get("queue_name")
        self.credentials = pika.PlainCredentials(self.broker_login, self.broker_pwd)
        self.conn_params = pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            credentials=self.credentials,
            heartbeat=600,
            blocked_connection_timeout=3000,
        )
        self.properties = pika.BasicProperties(
            delivery_mode=pika.DeliveryMode.Persistent
        )
        self.connection = None
        self.channel = None

    def __enter__(self):
        if self.connection is None or self.connection.is_closed():
            self.connection = pika.BlockingConnection(self.conn_params)
        if self.channel is None or self.channel.is_closed():
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue=self.queue_name, durable=True)
        return self

    def post_message(self, data: str, queue_name: str) -> None:
        logger.debug(
            "%s.post_message: data=%s, queue_name=%s"
            % (self.__class__.__name__, data, queue_name)
        )
        self.channel.queue_declare(queue=queue_name, durable=True)
        self.channel.basic_publish(
            exchange="",
            routing_key=queue_name,
            body=data,
            properties=self.properties,
        )
        logger.debug("%s.post_message - Message sent" % self.__class__.__name__)

    def consume(self):
        logger.debug("%s.consume" % self.__class__.__name__)
        if self.channel.is_open:
            self.channel.basic_consume(
                queue=self.queue_name, on_message_callback=self.callback, auto_ack=False
            )
        else:
            logger.exception("Channel is closed!")
            raise ChannelWrongStateError("Channel was closed!")
        try:
            logger.info("Start consuming")
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Consumer stopped by keyboard interruption.")
        finally:
            self.__exit__()

    def callback(self, ch, method, properties, message):
        try:
            assert isinstance(message, (str, bytes)), (
                "Данные поступили в недопутимом формате. data=%s" % message
            )
            try:
                data = json.loads(message)
            except JSONDecodeError as e:
                logger.error(
                    "JSONDecodeError has occured in %s.callback"
                    % self.__class__.__name__
                )
                logger.error("Error details:%s" % e)
                logger.debug(f"{self.__class__.__name__}.callback: message={message}")
                self.channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return None
            logger.debug(f"{self.__class__.__name__}.callback: data={data}")
        except AssertionError as e:
            logger.debug(f"{self.__class__.__name__}.callback: {e}")
            self.channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return None
        try:
            PreMessage.validate(data)
        except SchemaError as e:
            logger.error(f"{self.__class__.__name__}.callback: {e}")
            self.channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return None
        return self.process_request(data, method)

    def process_request(self, request, method):
        pass

    def __exit__(self, *args, **kwargs):
        if self.channel is not None or self.channel.is_open():
            self.channel.stop_consuming()
            self.channel.close()
        if self.connection is not None or self.connection.is_open():
            self.connection.close()
