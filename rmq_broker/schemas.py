from schema import Schema

PreMessage = Schema(
    {
        "request_type": str,
        "request_id": str,
        "header": {"src": str, "dst": str},
        "body": object,
    }
)
