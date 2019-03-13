import pytest
from mozilla_schema_creator.generic_ping import GenericPing
from mozilla_schema_creator.probes import MainProbe
from mozilla_schema_creator.schema import Schema

import pprint

"""
*******************
  Shared Fixtures
*******************
"""


@pytest.fixture
def schema():
    return {
        "type": "object",
        "properties": {
            "env": {
                "type": "string"
            },
            "top_level": {
                "type": "object",
                "additionalProperties": {
                    "type": "object"
                }
            },
            "nested": {
                "type": "object",
                "properties": {
                    "second_level": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "object"
                        }
                    }
                }
            }
        }
    }


@pytest.fixture
def env():
    return {
        "type": "object",
        "properties": {
            "env": {
                "type": "string"
            }
        }
    }


@pytest.fixture
def probes():
    return {
        "histogram/second_level_probe": {
            "name": "second_level_probe",
            "type": "histogram",
            "first_added": {
                "nightly": "2019-01-02 00:00:00"
            },
            "history": [
                {
                    "description": "Remember the Canterbury",
                    "second_level": True,
                    "details": {"keyed": False}
                }
            ]
        },
        "histogram/test_probe": {
            "name": "test_probe",
            "type": "histogram",
            "first_added": {
                "nightly": "2019-01-01 00:00:00"
            },
            "history": [
                {
                    "description": "Remember the Canterbury",
                    "second_level": False,
                    "details": {"keyed": False}
                }
            ]
        }
    }


"""
******************
  Shared Classes
******************
"""


class LocalMainPing(GenericPing):

    def __init__(self, schema, env, probes):
        self.schema = Schema(schema)
        self.env = Schema(env)
        self.probes = [MainProbe(k, v) for k, v in probes.items()]

    def get_schema(self):
        return self.schema

    def get_env(self):
        return self.env

    def get_probes(self):
        return self.probes

    def generate_schema(self, config, **kwargs):
        schemas = super().generate_schema(config, **kwargs)
        return {k: [s.schema for s in schema_list] for k, schema_list in schemas.items()}


"""
********************
  Shared Functions
********************
"""


def get_differences(a, b, path="", sep=" / "):
    res = []
    if a and not b:
        res.append(("Expected exists but not Actual", path))
    if b and not a:
        res.append(("Actual exists but not Expected", path))
    if not a and not b:
        return res

    a_dict, b_dict = isinstance(a, dict), isinstance(b, dict)
    a_list, b_list = isinstance(a, list), isinstance(b, list)
    if a_dict and not b_dict:
        res.append(("Expected dict but not Actual", path))
    elif b_dict and not a_dict:
        res.append(("Actual dict but not Expected", path))
    elif not a_dict and not b_dict:
        if a_list and b_list:
            for i, (ae, be) in enumerate(zip(a, b)):
                res = res + get_differences(ae, be, path + sep + str(i))
        elif a != b:
            res.append(("Expected={}, Actual={}".format(a, b), path))
    else:
        a_keys, b_keys = set(a.keys()), set(b.keys())
        a_not_b, b_not_a = a_keys - b_keys, b_keys - a_keys

        for k in a_not_b:
            res.append(("In Expected, not in Actual", path + sep + k))
        for k in b_not_a:
            res.append(("In Actual, not in Expected", path + sep + k))

        for k in (a_keys & b_keys):
            res = res + get_differences(a[k], b[k], path + sep + k)

    return res


def print_and_test(expected, result):
    pp = pprint.PrettyPrinter(indent=2)

    print("\nExpected:")
    pp.pprint(expected)

    print("\nActual:")
    pp.pprint(result)

    print("\nDifferences:")
    print('\n'.join([' - '.join(v) for v in get_differences(expected, result)]))

    assert(result == expected)
