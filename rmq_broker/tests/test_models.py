import pytest
from pydantic.error_wrappers import ValidationError

from rmq_broker.models import (
    BaseMessage,
    ErrorMessage,
    IncomingMessage,
    OutgoingMessage,
)
from rmq_broker.tests.factories import MessageFactory


class TestBaseMessage:
    def test_base_message_to_exclude(self):
        class TestMessage(BaseMessage):
            class Config:
                to_exclude = [
                    "header",
                ]

        message = TestMessage().generate()
        assert not message.get("header")


class TestOutgoingMessage:
    def test_outgoing_message_validation(self):
        message = MessageFactory.get_outgoing_message()
        validated_model = OutgoingMessage(**message)
        validated_message = validated_model.dict()
        assert isinstance(validated_message, dict)
        assert validated_message.get("status")

    def test_outgoing_message_validation_invalid_message(self):
        message = MessageFactory.get_invalid_message()
        with pytest.raises(ValidationError):
            OutgoingMessage(**message)

    def test_outgoing_message_generation(self):
        message = OutgoingMessage().generate()
        assert OutgoingMessage(**message)
        assert message["status"]["code"] == 200
        assert message["status"]["message"] == "OK"


class TestIncomingMessage:
    def test_incoming_message_validation_incoming_message(self):
        message = MessageFactory.get_incoming_message()
        validated_model = IncomingMessage(**message)
        validated_message = validated_model.dict()
        assert isinstance(validated_message, dict)
        assert not validated_message.get("status")

    def test_incoming_message_validation_with_status(self):
        message = MessageFactory.get_outgoing_message()
        validated_model = IncomingMessage(**message)
        validated_message = validated_model.dict()
        assert isinstance(validated_message, dict)
        assert validated_message.get("status")

    def test_incoming_message_validation_invalid_message(self):
        message = MessageFactory.get_invalid_message()
        with pytest.raises(ValidationError):
            IncomingMessage(**message)

    def test_incoming_message_generation(self):
        message = IncomingMessage().generate()
        assert IncomingMessage(**message)
        assert not message.get("status")


class TestErrorMessage:
    def test_error_message_generation(self):
        message = ErrorMessage().generate()
        assert OutgoingMessage(**message)
        assert message["status"]["code"] == 400
        assert message["status"]["message"] == "Error"
