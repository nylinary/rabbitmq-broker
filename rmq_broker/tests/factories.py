from uuid import uuid4


class MessageFactory:
    @staticmethod
    def get_incoming_message() -> dict:
        incoming_message = MessageFactory.get_outgoing_message()
        incoming_message.pop("status")
        return incoming_message

    @staticmethod
    def get_invalid_message() -> dict:
        invalid_message = MessageFactory.get_outgoing_message()
        invalid_message["header"].pop("src")
        return invalid_message

    @staticmethod
    def get_outgoing_message() -> dict:
        return {
            "request_id": uuid4().hex,
            "request_type": "sdfsd",
            "header": {"dst": "sdfsdfs", "src": "sdfdsfs"},
            "body": {},
            "status": {"code": 200, "message": "dsf"},
            "something_else": "smth else",
        }
