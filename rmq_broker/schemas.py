from typing import TypedDict

from schema import Optional, Or, Schema
from typing_extensions import NotRequired


class MessageHeader(TypedDict):
    dst: str
    src: str


class MessageStatus(TypedDict):
    code: int
    message: str


class BrokerMessage(TypedDict):
    request_type: str
    request_id: str
    header: MessageHeader
    body: dict


class IncomingMessage(BrokerMessage):
    status: NotRequired[MessageStatus]


class OutgoingMessage(BrokerMessage):
    status: MessageStatus


PreMessage = Schema(
    {
        "request_type": str,
        "request_id": str,
        "header": {"src": str, "dst": str},
        "body": object,
        Optional("status"): dict,
    }
)


PostMessage = Schema(
    {
        "request_type": str,
        "request_id": str,
        "header": {"src": str, "dst": str},
        "body": object,
        "status": {"message": str, "code": Or(int, str)},
    }
)

MessageTemplate = {
    "request_type": "",
    "request_id": "",
    "header": {"src": "", "dst": ""},
    "body": {},
    "status": {"message": "", "code": ""},
}
