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

    def test_set_elem_propagate(self):
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
                propagate=False)

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
                propagate=True)

        print_and_test(expected, res_schema.schema)

        # Deleting the elem again should match our original schema
        res_schema.delete_group_from_schema(
                ("properties", "b", "properties", "hello"),
                propagate=True)

        print_and_test(schema.schema, res_schema.schema)

    def test_valid_schema_change(self):
        _from = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "properties": {
                "first": {
                    "type": "string"
                }
            }
        }

        _to = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "properties": {
                "first": {
                    "type": "string"
                },
                "second": {
                    "type": "boolean"
                }
            }
        }

        assert len(Schema.is_valid_schema_change(_from, _to)) == 0

    def test_valid_schema_change__nested(self):
        _from = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "properties": {
                "first": {
                    "type": "object",
                    "properties": {
                        "a": {
                            "type": "string"
                        }
                    }
                }
            }
        }

        _to = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "properties": {
                "first": {
                    "type": "object",
                    "properties": {
                        "a": {
                            "type": "string"
                        },  
                        "b": {
                            "type": "boolean"
                        }
                    }
                }
            }
        }

        assert len(Schema.is_valid_schema_change(_from, _to)) == 0

    def test_valid_schema_change__make_nullable(self):
        _from = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "properties": {
                "first": {
                    "type": "string"
                },
                "second": {
                    "type": "string"
                }
            },
            "required": ["first"]
        }

        _to = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "properties": {
                "first": {
                    "type": "string"
                },
                "second": {
                    "type": ["string", "null"]
                }
            }
        }

        assert len(Schema.is_valid_schema_change(_from, _to)) == 0

    def test_invalid_schema_change__removing_column(self):
        _from = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "properties": {
                "first": {
                    "type": "string"
                },
                "second": {
                    "type": "boolean"
                }
            }
        }

        _to = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "properties": {
                "first": {
                    "type": "string"
                }
            }
        }

        assert len(Schema.is_valid_schema_change(_from, _to)) > 0

    def test_invalid_schema_change__changing_type(self):
        _from = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "properties": {
                "first": {
                    "type": "string"
                }
            }
        }

        _to = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "properties": {
                "first": {
                    "type": "boolean"
                }
            }
        }

        assert len(Schema.is_valid_schema_change(_from, _to)) == 1

    def test_valid_schema_change__to_non_required(self):
        _from = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "properties": {
                "first": {
                    "type": "string"
                }
            }
        }

        _to = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "properties": {
                "first": {
                    "type": ["string", "null"]
                }
            }
        }

        assert Schema.is_valid_schema_change(_from, _to) == {}
