from __future__ import annotations

from typing import Any, List, Tuple
from .utils import _get
from .probes import Probe
from .config import Config
from json import JSONEncoder
import copy


class SchemaException(Exception):
    pass


class SchemaEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Schema):
            return obj.schema
        if isinstance(obj, dict):
            return {k: self.default(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self.default(v) for v in obj]
        return JSONEncoder.default(self, obj)


# TODO: s/Schema/JSONSchema
class Schema(object):

    def __init__(self, schema: dict):
        self.schema = schema

    def set_schema_elem(self, key: Tuple[str], elem: Any) -> dict:
        new_elem = self.schema

        for k in key[:-1]:
            if k not in new_elem:
                new_elem[k] = {}
                if k == "properties":
                    new_elem["type"] = "object"
            new_elem = new_elem[k]

        new_elem[key[-1]] = elem

    def get_size(self) -> int:
        return self._get_schema_size(self.schema)

    def clone(self) -> Schema:
        return Schema(copy.deepcopy(self.schema))

    def make_schemas(self, env: Schema, probes: List[Probe], config: Config,
                     split: bool, max_size: int) -> List[Schema]:
        """
        Fill in probes based on the config, and keep only the env
        parts of the schema. Throw away everything else.
        """
        schema_elements = sorted(config.get_schema_elements(probes), key=lambda x: x[1])
        schemas = []

        # TODO: Should env be checked to be a subset of schema?
        final_schema = env.clone()
        for schema_key, probe in schema_elements:
            probe_schema = probe.get_schema()

            if split and final_schema.get_size() + probe_schema.get_size() > max_size:
                schemas.append(final_schema)
                final_schema = env.clone()

            final_schema.set_schema_elem(
                schema_key + ("properties", probe.name),
                probe_schema.schema)
            final_schema.set_schema_elem(
                schema_key + ("additionalProperties",),
                False)

        return schemas + [final_schema]

    def _delete_key(self, key: Tuple[str]):
        try:
            elem = _get(self.schema, key[:-1])
            del elem[key[-1]]
        except KeyError:
            return

    def _delete_group_from_schema(self, key: Tuple[str]):
        self._delete_key(key)

        # Now check, moving backwards, if that was the only available property
        # If it was, and there are no additionalProperties, delete the parent
        for subkey in reversed([key[:i] for i in range(len(key))]):
            if not subkey or subkey[-1] == "properties":
                # we only want to check the actual entry
                continue

            elem = _get(self.schema, subkey)
            if not elem["properties"] and not elem.get("additionalProperties", False):
                self._delete_key(subkey)

    def make_extra_schema(self, probes: List[Probe], configs: List[Config]):
        """
        Given the list of probes and the configuration,
        return the schema that has everything but those sections that we
        filled in already.

        TODO: Split the extra schema, when needed (e.g. extra.0.schema.json, extra.1.schema.json)
        """

        # Get the schema elements we already filled in for the other tables
        schema_elements = [
            schema_key
            for _config in configs
            for schema_key, _ in _config.get_schema_elements(probes)
        ]

        # Delete those from the schema
        for schema_key in schema_elements:
            self._delete_group_from_schema(schema_key)

    @staticmethod
    def _get_schema_size(schema: dict, key=None) -> int:
        if key is None:
            key = tuple()

        if isinstance(schema, list):
            return sum(Schema._get_schema_size(s) for s in schema)

        if "type" not in schema:
            raise Exception("Missing type for schema element at key " + "/".join(key))

        if isinstance(schema["type"], list):
            max_size = 0
            for t in schema["type"]:
                s = copy.deepcopy(schema)
                s["type"] = t
                max_size = max(max_size, Schema._get_schema_size(s, key))
            return max_size

        # TODO: Tests and finalize the different types available and how they map to BQ
        # e.g. (allOf, anyOf, etc.)
        if schema["type"] == "object":
            # Sometimes the "properties" field is empty...
            if "properties" in schema and schema["properties"]:
                # A ROW type with a known set of fields
                return sum((
                    Schema._get_schema_size(p, key=key + (n,))
                    for n, p in schema["properties"].items()))

            # A MAP type with key and value groups
            return 2

        if schema["type"] == "array":
            if "items" not in schema:
                raise Exception("Missing items for array schema element at key " + "/".join(key))
            # Arrays are repeated fields, get its size
            return Schema._get_schema_size(schema["items"], key=key + ("arr-items",))

        # Otherwise, assume a scalar value
        return 1
