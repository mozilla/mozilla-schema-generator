# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest

from .test_utils import LocalMainPing, env, probes, schema  # noqa F401
from mozilla_schema_generator.schema import SchemaException
from mozilla_schema_generator.config import Config


class TestPing(object):

    def test_env_max_size(self, schema, env, probes):  # noqa F811
        ping = LocalMainPing(schema, env, probes)

        with pytest.raises(SchemaException):
            ping.generate_schema(Config("default", {}), max_size=1)
