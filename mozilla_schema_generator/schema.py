# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


from __future__ import annotations

from typing import Any, Tuple
from .utils import _get
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

    def get(self, key: Tuple[str]) -> Any:
        return _get(self.schema, key)

    def get_size(self) -> int:
        return self._get_schema_size(self.schema)

    def clone(self) -> Schema:
        return Schema(copy.deepcopy(self.schema))

    def _delete_key(self, key: Tuple[str]):
        try:
            elem = _get(self.schema, key[:-1])
            del elem[key[-1]]
        except KeyError:
            return

    def delete_group_from_schema(self, key: Tuple[str]):
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
