# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import yaml
import pytest
from .test_utils import print_and_test
from mozilla_schema_generator import glean_ping
from mozilla_schema_generator.config import Config
from mozilla_schema_generator.utils import _get, prepend_properties

from typing import Dict, List


@pytest.fixture
def glean():
    return glean_ping.GleanPing("glean")


@pytest.fixture
def config():
    config_file = "./mozilla_schema_generator/configs/glean.yaml"
    with open(config_file) as f:
        return Config("glean", yaml.load(f))


class NoProbeGleanPing(glean_ping.GleanPing):
    def get_probes(self) -> List[Dict]:
        return []


class TestGleanPing(object):

    def test_env_size(self, glean):
        assert glean.get_env().get_size() > 0

    def test_single_schema(self, glean, config):
        schemas = glean.generate_schema(config, split=False)

        assert schemas.keys() == {"baseline", "events", "metrics", "deletion-request"}

        final_schemas = {k: schemas[k][0].schema for k in schemas}
        for name, schema in final_schemas.items():
            # A few parts of the generic structure
            assert "ping_info" in schema["properties"]
            assert "client_info" in schema["properties"]

            labeled_counters = _get(schema, prepend_properties(("metrics", "labeled_counter")))
            assert "glean.error.invalid_label" in labeled_counters['properties']

            if name == "baseline":
                # Device should be included, since it's a standard metric
                strings = _get(schema, prepend_properties(("metrics", "string")))
                assert "glean.baseline.locale" in strings["properties"]

    def test_get_repos(self):
        repos = glean_ping.GleanPing.get_repos()
        assert ("fenix", "org-mozilla-fenix") in repos

    def test_generic_schema(self, glean, config):
        schemas = glean.generate_schema(config, split=False, generic_schema=True)
        generic_schema = glean.get_schema().schema
        assert schemas.keys() == {"baseline", "events", "metrics", "deletion-request"}

        final_schemas = {k: schemas[k][0].schema for k in schemas}
        for name, schema in final_schemas.items():
            print_and_test(generic_schema, schema)

    def test_removing_additional_properties(self, config):
        # When there are no probes, previously all the addlProps
        # fields remained; we now remove them
        not_glean = NoProbeGleanPing("LeanGleanPingNoIding")
        schemas = not_glean.generate_schema(config, split=False)

        assert schemas.keys() == {"baseline", "events", "metrics", "deletion-request"}

        final_schemas = {k: schemas[k][0].schema for k in schemas}
        for name, schema in final_schemas.items():
            # The metrics key should have been deleted through
            # propagation
            assert "metrics" not in schema["properties"]
