"""Доработанные pydantic модели - могут быть использованы как для валидации,
так и для генерации сообщения.

Валидация сообщения происходит так же, как и в обычной pydantic модели:

    ProcessedMessage(**message_dict)

Для генерации сообщения необходимо создать объект модели, не передавая аргументы
при инициализации, и вызвать метод generate. В аргументы метода generate можно
передавать любой из ключей структуры сообщения, в том числе code, message,
dst и src. Вложенная структура(header, status) формируется сама:

    >>> ProcessedMessage().generate(dst="destination", code=201, request_type="creation")
    >>> {"header": {"src": "", "dst": "destination"}, "request_type": "creation"...}
"""

import inspect
from typing import Iterable, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel
from starlette import status as http_code


class MessageHeader(BaseModel):
    src: str
    dst: str


class MessageStatus(BaseModel):
    message: str
    code: int


class BaseMessage(BaseModel):
    request_type: str
    request_id: UUID
    body: Union[dict, Iterable]
    header: MessageHeader
    status: MessageStatus

    def __init__(self, **kwargs):
        """При вызове метода генерации сообщения, нужно создать экземляр модели,
        не инициализируя её и не передавая аргументы.
        Валидация происходит как в стандарной pydantic модели.
        """
        if kwargs:
            super().__init__(**kwargs)

    def generate(self, **fields) -> dict:
        """Генерирует сообщение."""
        flat_message = self.generate_flat_message(**fields)
        return self.get_structured_message(flat_message)

    def generate_flat_message(self, **fields) -> dict:
        """Заполняет плоскую структуру сообщения переданными значениями.
        Если значение не указано - берет его из DefaultValues.
        """
        flat_message = dict()
        for field_name, default_value in self.get_required_attributes().items():
            if value := fields.get(field_name):
                flat_message[field_name] = value
            else:
                flat_message[field_name] = default_value
        return flat_message

    def get_required_attributes(self) -> dict:
        """Отдает аттрибуты класса DefaultValues, относящиеся к
        ключам сообщения.
        """
        attributes = dict()
        for attr_info in inspect.getmembers(self.DefaultValues):
            if not attr_info[0].startswith("_"):
                if not inspect.ismethod(attr_info[1]):
                    attributes[attr_info[0]] = attr_info[1]
        return attributes

    def get_structured_message(self, flat_message: dict) -> dict:
        """Создает вложенность в плоском сообщении."""
        flat_message["header"] = {
            "dst": flat_message.pop("dst"),
            "src": flat_message.pop("src"),
        }

        flat_message["status"] = {
            "message": flat_message.pop("message"),
            "code": flat_message.pop("code"),
        }
        for field_name in self.Config.to_exclude:
            flat_message.pop(field_name)

        return flat_message

    def dict(
        self,
        *,
        include=None,
        exclude=None,
        by_alias=False,
        skip_defaults=None,
        exclude_unset=False,
        exclude_defaults=False,
        exclude_none=True,
    ):
        """Всегда исключать ключи со значением None."""
        return super().dict(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            skip_defaults=skip_defaults,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )

    class Config:
        """Ключи, которые нужно исключить после генерации сообщения."""

        to_exclude = []

    class DefaultValues:
        """Значения по умолчанию при генерации сообщения."""

        request_id: UUID = uuid4().hex
        request_type: str = ""
        body: dict = dict()
        src: str = ""
        dst: str = ""
        message: str = "OK"
        code: int = http_code.HTTP_200_OK


class ErrorMessage(BaseMessage):
    class DefaultValues(BaseMessage.DefaultValues):
        code = http_code.HTTP_400_BAD_REQUEST
        message = "Error"


class UnprocessedMessage(BaseMessage):
    status: Optional[MessageStatus]

    class Config:
        to_exclude = [
            "status",
        ]


class ProcessedMessage(BaseMessage):
    pass
