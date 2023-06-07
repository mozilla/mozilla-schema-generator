# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Tests for `mozilla-schema-generator` module.
"""

from mozilla_schema_generator.config import Config
from mozilla_schema_generator.probes import MainProbe

from .test_utils import LocalMainPing, env, print_and_test, probes, schema  # noqa F401


class TestIntegration(object):
    def test_full_representation(self, schema, env, probes):  # noqa F811
        config = Config(
            "default",
            {
                "top_level": {
                    "match": {
                        "table_group": "top_level",
                        "type": "histogram",
                        "second_level": False,
                    }
                },
                "nested": {
                    "second_level": {
                        "match": {
                            "table_group": "nested",
                            "type": "histogram",
                            "second_level": True,
                        }
                    }
                },
            },
        )

        expected = {
            "default": {
                "type": "object",
                "properties": {
                    "env": {"type": "string"},
                    "top_level": {
                        "type": "object",
                        "properties": {"test_probe": MainProbe.histogram_schema},
                    },
                    "nested": {
                        "type": "object",
                        "properties": {
                            "second_level": {
                                "type": "object",
                                "properties": {
                                    "second_level_probe": MainProbe.histogram_schema
                                },
                            }
                        },
                    },
                },
            }
        }

        ping = LocalMainPing(schema, env, probes)
        print_and_test(expected, ping.generate_schema(config))

    def test_non_env_or_probe_full(self, schema, env, probes):  # noqa F811
        # Add a new field that is neither probe nor env
        schema["properties"]["env_ignore"] = {"type": "string"}
        config = Config(
            "default",
            {
                "top_level": {
                    "match": {
                        "table_group": "top_level",
                        "type": "histogram",
                        "second_level": False,
                    }
                },
                "nested": {
                    "second_level": {
                        "match": {
                            "table_group": "nested",
                            "type": "histogram",
                            "second_level": True,
                        }
                    }
                },
            },
        )

        ping = LocalMainPing(schema, env, probes)
        result = ping.generate_schema(config)
        assert "env_ignore" in result["default"]["properties"]

    def test_contains(self, schema, env, probes):  # noqa F811
        probes["histogram/test_probe"]["history"]["nightly"][0]["arr"] = [
            "val1",
            "val2",
        ]
        probes["histogram/second_level_probe"]["history"]["nightly"][0]["arr"] = [
            "val2"
        ]

        config = Config(
            "default",
            {
                "top_level": {
                    "match": {
                        "table_group": "top_level",
                        "arr": {"contains": "val1"},
                        "second_level": False,
                    }
                }
            },
        )

        ping = LocalMainPing(schema, env, probes)
        result = ping.generate_schema(config)

        assert (
            "test_probe" in result["default"]["properties"]["top_level"]["properties"]
        )
