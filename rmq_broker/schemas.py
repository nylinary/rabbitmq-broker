from typing import TypedDict
from uuid import UUID

from typing_extensions import NotRequired


class MessageHeader(TypedDict):
    dst: str
    src: str


class MessageStatus(TypedDict):
    code: int
    message: str


class BrokerMessage(TypedDict):
    request_type: str
    request_id: UUID
    header: MessageHeader
    body: dict


class IncomingMessage(BrokerMessage):
    status: NotRequired[MessageStatus]


class OutgoingMessage(BrokerMessage):
    status: MessageStatus
