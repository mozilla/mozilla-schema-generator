# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest
import yaml

from mozilla_schema_generator.config import Config
from mozilla_schema_generator.main_ping import MainPing
from mozilla_schema_generator.schema import SchemaException

from .test_utils import LocalMainPing, env, probes, schema  # noqa F401


class TestPing(object):
    def test_env_max_size(self, schema, env, probes):  # noqa F811
        ping = LocalMainPing(schema, env, probes)

        with pytest.raises(SchemaException):
            ping.generate_schema(Config("default", {}), max_size=1)

    def test_schema_max_size(self):
        config_file = "./mozilla_schema_generator/configs/main.yaml"
        with open(config_file) as f:
            config = Config("main", yaml.safe_load(f))
            ping = MainPing()

            max_size = ping.generate_schema(config, max_size=MainPing.default_max_size)[
                "main"
            ][0].get_size()

            with pytest.raises(SchemaException):
                ping.generate_schema(config, max_size=max_size - 1)
