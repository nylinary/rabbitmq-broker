import functools
from enum import Enum

from pydantic import BaseConfig
from pydantic.fields import FieldInfo, ModelField
from pydantic.main import BaseModel
from pydantic.schema import TypeModelSet, get_flat_models_from_model
from pydantic.utils import lenient_issubclass


def get_flat_models_from_fields(fields, known_models: TypeModelSet) -> TypeModelSet:
    flat_models: TypeModelSet = set()
    for field in fields:
        flat_models |= get_flat_models_from_field(field, known_models=known_models)
    return flat_models


def get_flat_models_from_field(field, known_models: TypeModelSet) -> TypeModelSet:
    flat_models: TypeModelSet = set()

    if not lenient_issubclass(field, BaseModel):
        model_field = functools.partial(
            ModelField,
            type_=field,
            name="request_type",
            class_validators={},
            model_config=BaseConfig(),
        )(field_info=FieldInfo())
        flat_models |= get_flat_models_from_model(
            model_field.type_, known_models=known_models
        )
    elif lenient_issubclass(field, BaseModel) and field not in known_models:
        flat_models |= get_flat_models_from_model(field, known_models=known_models)
    elif lenient_issubclass(field, Enum):
        flat_models.add(field)
    return flat_models
