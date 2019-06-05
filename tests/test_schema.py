# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from mozilla_schema_generator.schema import Schema
from .test_utils import print_and_test


class TestSchema(object):

    def test_delete_group_from_schema(self):
        schema = Schema({
            "properties": {
                "a": {
                    "properties": {
                        "b": {"type": "string"}
                    }
                },
                "b": {"type": "string"}
            }
        })

        schema.delete_group_from_schema(("properties", "a", "properties", "b"))
        assert schema.schema == {"properties": {"b": {"type": "string"}}}

        schema.delete_group_from_schema(("properties", "b"))

    def test_schema_size(self):
        str_obj = {"type": "string"}
        assert Schema._get_schema_size(str_obj) == 1

        num_obj = {"type": "number"}
        assert Schema._get_schema_size(num_obj) == 1

        map_obj = {"type": "object"}
        assert Schema._get_schema_size(map_obj) == 2

        defined_obj = {"type": "object", "properties": {"str": {"type": "string"}}}
        assert Schema._get_schema_size(defined_obj) == 1

        arr = {"type": "array", "items": {"type": "string"}}
        assert Schema._get_schema_size(arr) == 1

        nested = {"type": "array", "items": {"type": "object", "properties": {"a": {"type": "string"}}}} # noqa E501
        assert Schema._get_schema_size(nested) == 1

        _tuple = {"type": "array", "items": [{"type": "string"}, {"type": "string"}]}
        assert Schema._get_schema_size(_tuple) == 2

    def test_set_elem_propogate(self):
        schema = Schema({
            "properties": {
                "a": {
                    "type": "int"
                }
            },
            "type": "object"
        })

        res_schema = schema.clone()

        # Shouldn't add it if not propogating
        res_schema.set_schema_elem(
                ("properties", "b", "properties", "hello"),
                {"type": "string"},
                propogate=False)

        print_and_test(schema.schema, res_schema.schema)

        # should add it if propogating
        expected = {
            "properties": {
                "a": {
                    "type": "int"
                },
                "b": {
                    "properties": {
                        "hello": {
                            "type": "string"
                        },
                    },
                    "type": "object"
                }
            },
            "type": "object"
        }

        res_schema.set_schema_elem(
                ("properties", "b", "properties", "hello"),
                {"type": "string"},
                propogate=True)

        print_and_test(expected, res_schema.schema)

        # Deleting the elem again should match our original schema
        res_schema.delete_group_from_schema(
                ("properties", "b", "properties", "hello"),
                propogate=True)

        print_and_test(schema.schema, res_schema.schema)
