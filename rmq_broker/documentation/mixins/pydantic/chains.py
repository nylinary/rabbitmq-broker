from typing import Tuple

from pydantic.schema import get_model_name_map, model_process_schema

from rmq_broker.documentation import REF_PREFIX
from rmq_broker.documentation.mixins.pydantic.utils import get_flat_models_from_fields


class PydanticModelsChainMixin:
    def get_model_definitions(
        self,
        *,
        flat_models: set,
        model_name_map: dict,
    ) -> dict:
        definitions = {}
        for model in flat_models:
            m_schema, m_definitions, m_nested_models = model_process_schema(
                model, model_name_map=model_name_map, ref_prefix=REF_PREFIX
            )
            definitions.update(m_definitions)
            model_name = model_name_map[model]
            if "description" in m_schema:
                m_schema["description"] = m_schema["description"].split("\f")[0]
            definitions[model_name] = m_schema
        return definitions

    def process_forms(self, models: list) -> Tuple[dict, dict]:
        flat_models = get_flat_models_from_fields(models, known_models=set())
        model_name_map = get_model_name_map(flat_models)
        definitions = self.get_model_definitions(
            flat_models=flat_models, model_name_map=model_name_map
        )
        return model_name_map, definitions
