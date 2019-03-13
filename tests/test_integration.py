"""
Tests for `mozilla-schema-creator` module.
"""
import pytest

from .test_utils import LocalMainPing, env, print_and_test, probes, schema
from mozilla_schema_creator.config import Config
from mozilla_schema_creator.probes import MainProbe
from mozilla_schema_creator.schema import Schema
import pprint

class TestIntegration(object):

    def test_full_representation(self, schema, env, probes):
        config = Config({
            "top_level": {
                "match": {
                    "table_group": "top_level",
                    "type": "histogram",
                    "second_level": False
                }
            },
            "nested": {
                "second_level": {
                    "match": {
                        "table_group": "nested",
                        "type": "histogram",
                        "second_level": True
                    }
                }
            }
        })

        expected = {
            "full": [
                {
                    "type": "object",
                    "properties": {
                        "env": {
                            "type": "string"
                        },
                        "top_level": {
                            "type": "object",
                            "properties": {
                                "test_probe": MainProbe.histogram_schema
                            },
                            "additionalProperties": False
                        },
                        "nested": {
                            "type": "object",
                            "properties": {
                                "second_level": {
                                    "additionalProperties": False,
                                    "type": "object",
                                    "properties": {
                                        "second_level_probe": MainProbe.histogram_schema
                                    }
                                }
                            }
                        }
                    }
                }
            ]
        }
                

        ping = LocalMainPing(schema, env, probes)
        print_and_test(expected, ping.generate_schema(config))


    def test_split_representation(self, schema, env, probes):
        config = Config({
            "top_level": {
                "match": {
                    "table_group": "top_level",
                    "type": "histogram",
                    "second_level": False
                }
            },
            "nested": {
                "second_level": {
                    "match": {
                        "table_group": "nested",
                        "type": "histogram",
                        "second_level": True
                    }
                }
            }
        })

        expected = {
            "extra": [env],
            "top_level": [
                {
                 "type": "object",
                    "properties": {
                        "env": {
                            "type": "string"
                        },
                        "top_level": {
                            "type": "object",
                            "properties": {
                                "test_probe": MainProbe.histogram_schema
                            },
                            "additionalProperties": False
                        }
                    }
                },
            ],
            "nested": [
                {
                 "type": "object",
                    "properties": {
                        "env": {
                            "type": "string"
                        },
                        "nested": {
                            "type": "object",
                            "properties": {
                                "second_level": {
                                    "type": "object",
                                    "properties": {
                                        "second_level_probe": MainProbe.histogram_schema
                                    },
                                    "additionalProperties": False
                                }
                            }
                        }
                    }
                }
            ]
        }

        ping = LocalMainPing(schema, env, probes)
        print_and_test(expected, ping.generate_schema(config, split=True))


    def test_non_env_or_probe_full(self, schema, env, probes):
        # Add a new field that is neither probe nor env
        schema["properties"]["env_ignore"] = {"type": "string"}
        config = Config({
            "top_level": {
                "match": {
                    "table_group": "top_level",
                    "type": "histogram",
                    "second_level": False
                }
            },
            "nested": {
                "second_level": {
                    "match": {
                        "table_group": "nested",
                        "type": "histogram",
                        "second_level": True
                    }
                }
            }
        })

        ping = LocalMainPing(schema, env, probes)
        result = ping.generate_schema(config)
        assert "env_ignore" in result["full"][0]["properties"]


    def test_non_env_or_probe_split(self, schema, env, probes):
        # Add a new field that is neither probe nor env - should be in "extra" table
        schema["properties"]["env_ignore"] = {"type": "string"}
        config = Config({
            "top_level": {
                "match": {
                    "table_group": "top_level",
                    "type": "histogram",
                    "second_level": False
                }
            },
            "nested": {
                "second_level": {
                    "match": {
                        "table_group": "nested",
                        "type": "histogram",
                        "second_level": True
                    }
                }
            }
        })

        ping = LocalMainPing(schema, env, probes)
        result = ping.generate_schema(config, split=True)
        assert "env_ignore" not in result["top_level"][0]["properties"]
        assert "env_ignore" not in result["nested"][0]["properties"]
        assert "env_ignore" in result["extra"][0]["properties"]


    def test_contains(self, schema, env, probes):
        probes["histogram/test_probe"]["history"][0]["arr"] = ["val1", "val2"]
        probes["histogram/second_level_probe"]["history"][0]["arr"] = ["val2"]

        config = Config({
            "top_level": {
                "match": {
                    "table_group": "top_level",
                    "arr": {
                        "contains": "val1"
                    },
                    "second_level": False
                }
            }
        })


        ping = LocalMainPing(schema, env, probes)
        result = ping.generate_schema(config)

        assert "test_probe" in result["full"][0]["properties"]["top_level"]["properties"]

    def test_max_size(self, schema, env, probes):
        # Test that we split into multiple tables when we exceed max_size of columns
        probes["histogram/third_probe"] = {
            "history": [
                {
                    "second_level": False,
                    "details": {"keyed": False}
                }
            ],
            "type": "histogram",
            "name": "third_probe",
            "first_added": {
                "nightly": "2019-01-01 00:00:00"
            }
        }

        config = Config({
            "top_level": {
                "match": {
                    "table_group": "single",
                    "type": "histogram",
                    "second_level": False
                }
            },
            "nested": {
                "second_level": {
                    "match": {
                        "table_group": "single",
                        "type": "histogram",
                        "second_level": True
                    }
                }
            }
        })

        expected = {
            "extra": [env],
            "single": [
                {
                    "type": "object",
                    "properties": {
                        "env": {
                            "type": "string"
                        },
                        "top_level": {
                            "type": "object",
                            "properties": {
                                "test_probe": MainProbe.histogram_schema,
                                "third_probe": MainProbe.histogram_schema
                            },
                            "additionalProperties": False
                        }
                    }
                },
                {
                    "type": "object",
                    "properties": {
                        "env": {
                            "type": "string"
                        },
                        "nested": {
                            "type": "object",
                            "properties": {
                                "second_level": {
                                    "additionalProperties": False,
                                    "type": "object",
                                    "properties": {
                                        "second_level_probe": MainProbe.histogram_schema
                                    }
                                }
                            }
                        }
                    }
                }
            ]
        } 

        ping = LocalMainPing(schema, env, probes)
        result = ping.generate_schema(config, split=True, max_size=13)
        print_and_test(expected, result)
