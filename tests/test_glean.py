# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import yaml
import pytest
from mozilla_schema_generator import glean_ping
from mozilla_schema_generator.config import Config


@pytest.fixture
def glean():
    return glean_ping.GleanPing()


@pytest.fixture
def config():
    config_file = "./configs/glean.yaml"
    with open(config_file) as f:
        return Config(yaml.load(f))


class TestGleanPing(object):

    def test_env_size(self, glean):
        assert glean.get_env().get_size() > 0

    def test_single_schema(self, glean, config):
        schema = glean.generate_schema(config)["full"][0].schema

        assert "metrics" in schema["properties"]
        assert "ping_info" in schema["properties"]
