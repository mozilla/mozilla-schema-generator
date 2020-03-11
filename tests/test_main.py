# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import yaml
import pytest
from mozilla_schema_generator import main_ping
from mozilla_schema_generator.config import Config
from mozilla_schema_generator.utils import _get, prepend_properties


@pytest.fixture
def main():
    return main_ping.MainPing()


@pytest.fixture
def config():
    config_file = "./mozilla_schema_generator/configs/main.yaml"
    with open(config_file) as f:
        return Config("main", yaml.load(f))


class TestCommonPing(object):

    def test_env_size(self, main):
        assert main.get_env().get_size() > 0

    def test_single_schema(self, main, config):
        schema = main.generate_schema(config)["main"][0].schema

        assert "environment" in schema["properties"]
        assert "payload" in schema["properties"]
        assert _get(schema, prepend_properties(("environment", "settings", "userPrefs"))) \
            == {"type": "object", "additionalProperties": {"type": "string"}}
        assert _get(schema, prepend_properties(("environment", "system", "os", "version"))) \
            == {"type": "string"}
        assert "extension" in \
            _get(schema, prepend_properties(("payload", "processes")))["properties"]

    def test_min_probe_version(self, main):
        probes = main.get_probes()
        assert max([int(p.definition["versions"]["last"]) for p in probes]) >= main.MIN_FX_VERSION

    def test_split_schema(self, main, config):
        schema = main.generate_schema(config, split=True)

        expected = {"histograms", "scalars", "keyed_histograms", "keyed_scalars", "extra"}
        assert set(schema.keys()) == expected

        for k, schemas in schema.items():
            for s in schemas:
                assert "environment" in s.schema["properties"]
                assert "payload" in s.schema["properties"]
