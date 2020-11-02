# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from typing import Dict, List

import pytest
import requests
import yaml

from mozilla_schema_generator import glean_ping
from mozilla_schema_generator.config import Config
from mozilla_schema_generator.utils import _get, prepend_properties

from .test_utils import print_and_test


@pytest.fixture
def glean():
    return glean_ping.GleanPing({"name": "glean", "app_id:": "org-mozilla-glean"})


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

            labeled_counters = _get(
                schema, prepend_properties(("metrics", "labeled_counter"))
            )
            assert "glean.error.invalid_label" in labeled_counters["properties"]

            if name == "baseline":
                # Device should be included, since it's a standard metric
                strings = _get(schema, prepend_properties(("metrics", "string")))
                assert "glean.baseline.locale" in strings["properties"]

    def test_get_repos(self):
        repos = glean_ping.GleanPing.get_repos()
        names_ids = [(r["name"], r["app_id"]) for r in repos]
        assert ("fenix", "org-mozilla-fenix") in names_ids

    def test_generic_schema(self, glean, config):
        schemas = glean.generate_schema(config, split=False, generic_schema=True)
        assert schemas.keys() == {"baseline", "events", "metrics", "deletion-request"}

        final_schemas = {k: schemas[k][0].schema for k in schemas}
        for name, schema in final_schemas.items():
            generic_schema = glean.get_schema().schema
            generic_schema["mozPipelineMetadata"] = {
                "bq_dataset_family": "org_mozilla_glean",
                "bq_metadata_format": "structured",
                "bq_table": name.replace("-", "_") + "_v1",
            }
            print_and_test(generic_schema, schema)

    def test_missing_data(self, config):
        # When there are no files, this should error
        repo = {"name": "LeanGleanPingNoIding", "app_id": "org-mozilla-lean"}
        not_glean = NoProbeGleanPing(repo)
        with pytest.raises(requests.exceptions.HTTPError):
            not_glean.generate_schema(config, split=False)
