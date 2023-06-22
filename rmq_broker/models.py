from uuid import UUID, uuid4

from pydantic import BaseModel
from pydantic.fields import Field
from starlette import status as status_code


class BaseMessage(BaseModel):
    _nest = dict

    def dict(
        self,
        *,
        include=None,
        exclude=None,
        by_alias=False,
        skip_defaults=None,
        exclude_unset=False,
        exclude_defaults=False,
        exclude_none=False,
    ):
        data = super().dict(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            skip_defaults=skip_defaults,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )
        return self.__post_dict__(data)

    def __post_dict__(self, data: dict) -> dict:
        for field_name in self._nest.keys():
            field = {field_name: {}}
            for _field_name in self._nest[field_name]:
                field[field_name].update({_field_name: data.pop(_field_name, None)})
            data.update(field)
        return data


class OutgoingMessage(BaseMessage):
    request_type: str = ""
    request_id: UUID = Field(default=uuid4().hex)
    body: dict = Field(default_factory=dict)
    src: str = ""
    dst: str = ""
    message: str = "OK"
    code: int = status_code.HTTP_200_OK

    _nest = {"header": ["dst", "src"], "status": ["message", "code"]}


class IncomingMessage(OutgoingMessage):
    def __init__(self, allow_status: bool = False, **data):
        super().__init__(**data)
        if not allow_status:
            del self._nest["status"], self.code, self.message


class ErrorMessage(OutgoingMessage):
    code: int = status_code.HTTP_500_INTERNAL_SERVER_ERROR
    message: str = "Unknown error"
