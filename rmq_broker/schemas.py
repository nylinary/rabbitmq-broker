from typing import TypedDict
from uuid import UUID

from typing_extensions import NotRequired


class BrokerMessageHeader(TypedDict):
    dst: str
    src: str


class BrokerMessageStatus(TypedDict):
    code: int
    message: str


class BrokerMessage(TypedDict):
    request_type: str
    request_id: UUID
    header: BrokerMessageHeader
    body: dict


class UnprocessedBrokerMessage(BrokerMessage):
    status: NotRequired[BrokerMessageStatus]


class ProcessedBrokerMessage(BrokerMessage):
    status: BrokerMessageStatus
