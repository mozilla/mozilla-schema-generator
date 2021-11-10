# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from typing import Dict, List
from unittest.mock import patch

import pytest
import requests
import yaml

from mozilla_schema_generator import glean_ping
from mozilla_schema_generator.config import Config
from mozilla_schema_generator.probes import GleanProbe
from mozilla_schema_generator.utils import _get, prepend_properties

from .test_utils import print_and_test


@pytest.fixture
def glean():
    return glean_ping.GleanPing({"name": "glean-core", "app_id": "org-mozilla-glean"})


@pytest.fixture
def config():
    config_file = "./mozilla_schema_generator/configs/glean.yaml"
    with open(config_file) as f:
        return Config("glean", yaml.load(f))


class NoProbeGleanPing(glean_ping.GleanPing):
    def get_probes(self) -> List[Dict]:
        return []


class GleanPingWithUrlMetric(glean_ping.GleanPing):
    def get_probes(self) -> List[GleanProbe]:
        probe_defn = {
            "history": [
                {
                    "description": "Glean URL test description",
                    "dates": {
                        "first": "2019-04-12 13:44:13",
                        "last": "2019-08-08 15:34:03",
                    },
                    "send_in_pings": ["metrics"],
                },
            ],
            "name": "my_url",
            "type": "url",
            "in-source": False,
        }
        probe = GleanProbe("metrics", probe_defn, pings=["metrics"])
        return [p for p in super().get_probes()] + [probe]


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

    def test_pings(self, glean):
        # FIXME: this only tests the case where a repo has no dependencies-- ideally
        # we would test the dependency resolution algorithm as well
        RETURN_VALUES = [{"foo": {"history": [{"description": "baz"}]}}, {}, {}, {}]
        with patch.object(
            glean_ping.GleanPing,
            "_get_json",
            side_effect=RETURN_VALUES + RETURN_VALUES,
        ):
            assert set(glean.get_pings()) == {
                "foo",
            }
            assert glean.get_ping_descriptions() == {"foo": "baz"}

    def test_generic_schema(self, glean, config):
        schemas = glean.generate_schema(config, split=False, generic_schema=True)
        assert schemas.keys() == {"baseline", "events", "metrics", "deletion-request"}

        final_schemas = {k: schemas[k][0].schema for k in schemas}
        for name, schema in final_schemas.items():
            generic_schema = glean.get_schema(generic_schema=True).schema
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

    def test_retention_days(self, config):
        glean = glean_ping.GleanPing(
            {"name": "glean-core", "app_id": "org-mozilla-glean", "retention_days": 90}
        )
        schemas = glean.generate_schema(config, split=False, generic_schema=True)

        final_schemas = {k: schemas[k][0].schema for k in schemas}
        for name, schema in final_schemas.items():
            assert (
                schema["mozPipelineMetadata"]["expiration_policy"]["delete_after_days"]
                == 90
            )

    def test_encryption_exists(self, config):
        glean = glean_ping.GleanPing(
            {
                "name": "glean-core",
                "in-source": True,
                "app_id": "org-mozilla-glean",
                "encryption": {"use_jwk": True},
            }
        )
        schemas = glean.generate_schema(config, split=False, generic_schema=True)

        final_schemas = {k: schemas[k][0].schema for k in schemas}
        for name, schema in final_schemas.items():
            jwe_mappings = schema["mozPipelineMetadata"]["jwe_mappings"]
            assert len(jwe_mappings) == 1
            assert set(jwe_mappings[0].keys()) == {
                "source_field_path",
                "decrypted_field_path",
            }

    def test_rally_metadata_format(self, config):
        glean = glean_ping.GleanPing(
            {
                "name": "rally-debug",
                "in-source": True,
                "app_id": "rally_debug",
                "encryption": {"use_jwk": True},
            }
        )
        schemas = glean.generate_schema(config, split=False, generic_schema=True)

        final_schemas = {k: schemas[k][0].schema for k in schemas}
        for name, schema in final_schemas.items():
            metadata_format = schema["mozPipelineMetadata"]["bq_metadata_format"]
            assert metadata_format == "pioneer"

    def test_bug_1737656_affected(self, config):
        glean = glean_ping.GleanPing(
            {
                # This ping exists in the static list of affected pings.
                "name": "rally-debug",
                "in-source": True,
                "app_id": "rally_debug",
            }
        )
        schemas = glean.generate_schema(config, split=False)

        final_schemas = {k: schemas[k][0].schema for k in schemas}
        for name, schema in final_schemas.items():
            metrics_text = schema["properties"]["metrics"]["properties"]["text"]
            assert metrics_text is not None
            assert type(metrics_text.get("additionalProperties")) is dict

    def test_bug_1737656_unaffected(self, config):
        glean = glean_ping.GleanPing(
            {
                # This ping does not exist in the static list of affected pings.
                "name": "glean-core",
                "in-source": True,
                "app_id": "org-mozilla-glean",
            }
        )
        schemas = glean.generate_schema(config, split=False)

        final_schemas = {k: schemas[k][0].schema for k in schemas}
        for name, schema in final_schemas.items():
            metrics_text = schema["properties"]["metrics"]["properties"].get("text")
            assert metrics_text is None

    def test_url_to_url2(self, config):
        glean = GleanPingWithUrlMetric(
            {
                # This ping does not exist in the static list of affected pings.
                "name": "glean-core",
                "in-source": False,
                "app_id": "org-mozilla-glean",
            }
        )
        schemas = glean.generate_schema(config, split=False)

        final_schemas = {k: schemas[k][0].schema for k in schemas}
        schema = final_schemas.get("metrics")
        assert "url" not in schema["properties"]["metrics"]["properties"].keys()
        assert "url2" in schema["properties"]["metrics"]["properties"].keys()
        assert list(
            (schema["properties"]["metrics"]["properties"]["url2"]["properties"].keys())
        ) == ["my_url"]
