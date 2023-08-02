from collections import defaultdict
from typing import Tuple

from rmq_broker.async_chains.base import BaseChain as AsyncBaseChain
from rmq_broker.async_chains.base import ChainManager
from rmq_broker.chains.base import BaseChain
from rmq_broker.schemas import ProcessedBrokerMessage, UnprocessedBrokerMessage
from rmq_broker.settings import settings

from . import REF_PREFIX
from .models import OpenAPI
from .utils import get_class_dir


class BaseDocsChain:
    openapi: dict = {}
    title: str = settings.SERVICE_NAME
    openapi_version: str = "3.0.2"
    version: str = "0.1"
    include_in_schema = False

    def make_chain_description(self, chain: BaseChain, model_name_map: dict) -> dict:
        name = chain.__class__.__name__
        required = getattr(chain, "body_model", None) in model_name_map
        # todo: Обязательность относительно обязательных параметров формы
        operation = {
            "tags": [f"RPC: {get_class_dir(chain)}"],
            "summary": name,
            "description": chain.__class__.__doc__,
            "operationId": chain.request_type,
        }
        if chain.deprecated:
            operation["deprecated"] = True
        if chain.actual:
            operation["deprecated"] = True
            operation["summary"] += ". Актуальный - " + chain.actual + "."
        request_body = {
            "required": required,
        }
        if required:
            model_name = model_name_map.get(chain.body_model)
            request_body["content"] = {
                "application/json": {"schema": {"$ref": f"{REF_PREFIX}{model_name}"}}
            }
        operation["requestBody"] = request_body
        return operation

    def process_forms(self, models: list) -> Tuple[dict, dict]:
        return {}, {}

    def make_openapi(
        self,
        chain_manager: ChainManager,
    ) -> dict:
        output: dict = {
            "openapi": self.openapi_version,
            "info": {"title": self.title, "version": self.version},
        }
        chains = [
            chain()
            for chain in chain_manager.chains.values()
            if chain.include_in_schema
        ]
        components: dict = {}
        paths = defaultdict(dict)

        typed_requests = [
            chain.body_model for chain in chains if getattr(chain, "body_model", None)
        ]
        model_name_map, definitions = self.process_forms(models=typed_requests)

        for chain in chains:
            operation = self.make_chain_description(chain, model_name_map)
            name = "/" + get_class_dir(chain) + "/" + chain.request_type
            paths[name]["post"] = operation

        if definitions:
            components["schemas"] = {k: definitions[k] for k in sorted(definitions)}
        if components:
            output["components"] = components
        output["paths"] = dict(
            sorted(paths.items(), key=lambda i: i[1]["post"]["tags"][0])
        )
        return OpenAPI(**output).dict(by_alias=True, exclude_none=True)


class DocsChain(BaseDocsChain, BaseChain):
    def get_response_body(
        self, data: UnprocessedBrokerMessage
    ) -> ProcessedBrokerMessage:
        if not self.openapi:
            self.openapi = self.make_openapi(chain_manager=ChainManager())
        return self.form_response(data, self.openapi)


class AsyncDocsChain(BaseDocsChain, AsyncBaseChain):
    async def get_response_body(
        self, data: UnprocessedBrokerMessage
    ) -> ProcessedBrokerMessage:
        if not self.openapi:
            self.openapi = self.make_openapi(chain_manager=ChainManager())
        return self.form_response(data, self.openapi)
