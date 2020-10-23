# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest

from mozilla_schema_generator import common_ping
from mozilla_schema_generator.config import Config
from mozilla_schema_generator.utils import _get, prepend_properties


@pytest.fixture
def ping():
    schema_url = (
        "https://raw.githubusercontent.com/mozilla-services/mozilla-pipeline-schemas"
        "/{branch}/schemas/telemetry/event/event.4.schema.json"
    )
    return common_ping.CommonPing(schema_url)


@pytest.fixture
def config():
    return Config("event", {})


class TestCommonPing(object):
    def test_env_size(self, ping):
        assert ping.get_env().get_size() > 0

    def test_single_schema(self, ping, config):
        schema = ping.generate_schema(config)["event"][0].schema

        assert "environment" in schema["properties"]
        assert _get(
            schema, prepend_properties(("environment", "settings", "userPrefs"))
        ) == {
            "type": "object",
            "description": "User preferences - limited to an allowlist defined in `toolkit/components/telemetry/app/TelemetryEnvironment.jsm`",  # NOQA
            "additionalProperties": {"type": "string"},
        }
