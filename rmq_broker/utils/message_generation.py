from rmq_broker.schemas import OutgoingMessage, MessageTemplate, IncomingMessage
from uuid import uuid4
from starlette import status
from copy import deepcopy

class Message:

    def get_message_template() -> OutgoingMessage:
        return deepcopy(MessageTemplate)
    
    def make_request_msg(
            request_type: str, 
            body: dict, 
            service_name: str,
            dst_service_name: str,
            request_id: str = uuid4().hex
            ) -> IncomingMessage:
        return {
            "request_id": request_id,
            "request_type": request_type,
            "header": {
                "src": service_name,
                "dst": dst_service_name,
            },
            "body": body,
        }
    
    def make_error_msg(
            request_id: str = uuid4().hex,
            request_type: str = "",
            service_name: str = "",
            dst_service_name: str = "",
            error: str = "Unknown error",
            status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
            ) -> OutgoingMessage:
        return {
            "request_id": request_id,
            "request_type": request_type,
            "header": {
                "src": service_name,
                "dst": dst_service_name,
            },
            "body": {},
            "status": {
                "message": error,
                "code": status_code
            }
        }