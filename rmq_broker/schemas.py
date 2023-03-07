from schema import Optional, Or, Schema

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
