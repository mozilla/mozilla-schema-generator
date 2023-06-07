# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest
import yaml

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
        return Config("main", yaml.safe_load(f))


class TestMainPing(object):
    def test_env_size(self, main):
        assert main.get_env().get_size() > 0

    def test_single_schema(self, main, config):
        schema = main.generate_schema(config)["main"].schema

        assert "environment" in schema["properties"]
        assert "payload" in schema["properties"]
        assert _get(
            schema, prepend_properties(("environment", "settings", "userPrefs"))
        ) == {
            "type": "object",
            "description": "User preferences - limited to an allowlist defined in `toolkit/components/telemetry/app/TelemetryEnvironment.jsm`",  # NOQA
            "additionalProperties": {"type": "string"},
        }
        assert (
            "extension"
            in _get(schema, prepend_properties(("payload", "processes")))["properties"]
        )

    def test_min_probe_version(self, main):
        probes = main.get_probes()
        assert (
            max([int(p.definition["versions"]["last"]) for p in probes])
            >= main.MIN_FX_VERSION
        )
