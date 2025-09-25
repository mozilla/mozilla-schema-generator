# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from typing import Dict, List
from unittest.mock import patch

import pytest
import requests
import yaml

from mozilla_schema_generator import generic_ping, glean_ping
from mozilla_schema_generator.config import Config
from mozilla_schema_generator.probes import GleanProbe
from mozilla_schema_generator.schema import Schema
from mozilla_schema_generator.utils import _get, prepend_properties

from .test_utils import print_and_test


@pytest.fixture
def glean():
    return glean_ping.GleanPing({"name": "glean-core", "app_id": "org-mozilla-glean"})


@pytest.fixture
def config():
    config_file = "./mozilla_schema_generator/configs/glean.yaml"
    with open(config_file) as f:
        return Config("glean", yaml.safe_load(f))


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


class GleanPingStub(glean_ping.GleanPing):
    def get_dependencies(self):
        repos = glean_ping.GleanPing.get_repos()
        current_repo = next((x for x in repos if x.get("app_id") == self.repo_name), {})
        return current_repo.get("dependencies", [])

    def _get_history(self):
        return []

    def _get_dependency_pings(self, dependency):
        return {
            "dependency_ping": {
                "in-source": True,
                "moz_pipeline_metadata": {
                    "bq_dataset_family": "glean_base",
                    "bq_metadata_format": "structured",
                    "bq_table": "dependency_ping_v1",
                },
                "name": "dependency_ping",
            }
        }

    def _get_ping_data_without_dependencies(self) -> Dict[str, Dict]:
        return {
            "ping1": {
                "in-source": True,
                "moz_pipeline_metadata": self.ping_metadata,
                "name": "ping1",
                "history": self._get_history(),
            }
        }

    def _get_metadata_overrides(self):
        return {}


class GleanPingWithExpirationPolicy(GleanPingStub):
    ping_metadata = {
        "bq_dataset_family": "app1",
        "bq_metadata_format": "structured",
        "bq_table": "ping1_v1",
        "expiration_policy": {
            "delete_after_days": 12,
            "collect_through_date": "2022-06-10",
        },
        "include_info_sections": True,
        "include_client_id": True,
    }


class GleanPingWithEncryption(GleanPingStub):
    ping_metadata = {
        "bq_dataset_family": "app1",
        "bq_metadata_format": "structured",
        "bq_table": "ping1_v1",
        "include_info_sections": True,
        "include_client_id": True,
        "jwe_mappings": [
            {
                "decrypted_field_path": "",
                "source_field_path": "/payload",
            }
        ],
    }


class GleanPingNoMetadata(GleanPingStub):
    ping_metadata = {
        "bq_dataset_family": "app1",
        "bq_metadata_format": "structured",
        "bq_table": "ping1_v1",
        "include_info_sections": True,
        "include_client_id": True,
    }


class GleanPingWithOverrideAttributes(GleanPingStub):
    ping_metadata = {
        "bq_dataset_family": "app1",
        "bq_metadata_format": "structured",
        "bq_table": "ping1_v1",
        "include_info_sections": True,
        "include_client_id": True,
        "override_attributes": [{"name": "geo_city", "value": None}],
    }


class GleanPingWithGranularity(GleanPingStub):
    ping_metadata = {
        "bq_dataset_family": "app1",
        "bq_metadata_format": "structured",
        "bq_table": "ping1_v1",
        "include_info_sections": True,
        "include_client_id": True,
        "submission_timestamp_granularity": "seconds",
    }


class GleanPingNoInfoSection(GleanPingStub):
    ping_metadata = {
        "bq_dataset_family": "app1",
        "bq_metadata_format": "structured",
        "bq_table": "ping1_v1",
        "include_info_sections": False,
        "include_client_id": True,
    }

    def _get_history(self):
        return [{"include_info_sections": False}]


class GleanPingNoInfoSectionWithHistory(GleanPingStub):
    ping_metadata = {
        "bq_dataset_family": "app1",
        "bq_metadata_format": "structured",
        "bq_table": "ping1_v1",
        "include_info_sections": False,
        "include_client_id": True,
    }

    def _get_history(self):
        return [{"include_info_sections": True}, {"include_info_sections": False}]


class GleanPingWithMultiplePings(GleanPingStub):
    ping1_metadata = {
        "bq_dataset_family": "app1",
        "bq_metadata_format": "structured",
        "bq_table": "ping1_v1",
        "expiration_policy": {"delete_after_days": 30},
        "include_info_sections": True,
        "include_client_id": True,
        "override_attributes": [{"name": "geo_city", "value": None}],
        "submission_timestamp_granularity": "seconds",
    }

    ping2_metadata = {
        "bq_dataset_family": "app1",
        "bq_metadata_format": "structured",
        "bq_table": "ping2_v1",
        "expiration_policy": {"delete_after_days": 45},
        "include_info_sections": True,
        "include_client_id": True,
        "submission_timestamp_granularity": "millis",
    }

    def _get_ping_data_without_dependencies(self) -> Dict[str, Dict]:
        return {
            "ping1": {
                "in-source": True,
                "moz_pipeline_metadata": self.ping1_metadata,
                "name": "ping1",
            },
            "ping2": {
                "in-source": True,
                "moz_pipeline_metadata": self.ping2_metadata,
                "name": "ping2",
            },
        }


class GleanPingWithMetadataOverrides(GleanPingStub):
    ping_metadata = {
        "bq_dataset_family": "app1",
        "bq_metadata_format": "structured",
        "bq_table": "ping_v1",
        "include_info_sections": True,
    }

    def get_dependencies(self):
        return ["dependency"]

    def _get_ping_data_without_dependencies(self) -> Dict[str, Dict]:
        return {
            "ping1": {
                "in-source": True,
                "moz_pipeline_metadata": self.ping_metadata,
                "name": "ping1",
            },
        }

    def _get_dependency_pings(self, dependency):
        return {
            "dependency_ping1": {
                "in-source": True,
                "moz_pipeline_metadata": {
                    "bq_dataset_family": "test",
                },
                "name": "dependency_ping1",
            },
            "dependency_ping2": {
                "in-source": True,
                "moz_pipeline_metadata": {
                    "bq_dataset_family": "test",
                    "expiration_policy": {"delete_after_days": 120},
                },
                "name": "dependency_ping2",
            },
            "dependency_ping3": {
                "in-source": True,
                "moz_pipeline_metadata": {
                    "bq_dataset_family": "test",
                },
                "name": "dependency_ping3",
            },
        }

    def get_repos(self):
        return [
            {
                "app_id": "app1",
                "moz_pipeline_metadata": {
                    "dependency_ping2": {
                        "expiration_policy": {"delete_after_days": 90}
                    },
                    "dependency_ping3": {
                        "expiration_policy": {"delete_after_days": 100},
                        "override_attributes": [{"name": "geo_city", "value": None}],
                    },
                },
                "moz_pipeline_metadata_defaults": {
                    "expiration_policy": {"delete_after_days": 80}
                },
            }
        ]


class TestGleanPing(object):
    def test_env_size(self, glean):
        assert glean.get_env().get_size() > 0

    def test_single_schema(self, glean, config):
        schemas = glean.generate_schema(config)

        assert schemas.keys() == {
            "baseline",
            "events",
            "metrics",
            "deletion-request",
            "health",
        }

        final_schemas = {k: schemas[k].schema for k in schemas}
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
        RETURN_VALUES = [{"foo": {"history": [{"description": "baz"}]}}, {}, {}]
        with patch.object(
            glean_ping.GleanPing,
            "_get_json",
            side_effect=RETURN_VALUES + RETURN_VALUES,
        ):
            assert set(glean.get_pings()) == {
                "foo",
            }
            assert glean.get_ping_descriptions() == {"foo": "baz"}

    def test_is_field_included(self):
        """Should return False if all history items have the field set to false."""
        field_name = "include_info_sections"
        ping_false_client_info = {
            "history": [
                {field_name: False},
                {field_name: False},
                {field_name: False},
            ]
        }
        actual = glean_ping.GleanPing._is_field_included(
            ping_false_client_info, field_name
        )
        assert actual is False

    def test_is_field_not_included(self):
        """Should return True if any history item has the given field set to true."""
        field_name = "include_info_sections"
        ping_false_client_info = {
            "history": [
                {field_name: False},
                {field_name: True},
                {field_name: False},
            ]
        }
        actual = glean_ping.GleanPing._is_field_included(
            ping_false_client_info, field_name
        )
        assert actual is True

    def test_is_field_not_found(self):
        """Should return True if any history item does not have the given field."""
        field_name = "include_client_id"
        ping_false_client_info = {
            "history": [
                {field_name: False},
                {},
                {field_name: False},
            ]
        }
        actual = glean_ping.GleanPing._is_field_included(
            ping_false_client_info, field_name
        )
        assert actual is True

    def test_dependencies(self, glean):
        RETURN_VALUES = {"glean-core": {"name": "glean-core", "type": "dependency"}}
        with patch.object(
            glean,
            "_get_json",
            return_value=RETURN_VALUES,
        ):
            assert set(glean.get_dependencies()) == {
                "glean-core",
            }

    def test_probes(self, glean):
        RETURN_VALUES = {
            "test.probe": {
                "history": [
                    {
                        "dates": {
                            "first": "2023-11-27 21:59:53",
                            "last": "2024-01-05 17:36:15",
                        },
                        "description": "description",
                        "expires": "never",
                        "type": "string",
                        "version": 0,
                    }
                ],
                "in-source": True,
                "name": "test.probe",
                "type": "string",
            }
        }

        with patch.object(glean, "get_dependencies", return_value=[]):
            with patch.object(
                glean,
                "_get_json",
                return_value=RETURN_VALUES,
            ):
                probes = glean.get_probes()
                assert len(probes) == 1
                assert probes[0].id == "test.probe"
                assert probes[0].type == "string"

    def test_probes_multiple_types(self, glean):
        RETURN_VALUES = {
            "test.probe": {
                "history": [
                    {
                        "dates": {
                            "first": "2023-11-27 21:59:53",
                            "last": "2024-01-05 17:36:15",
                        },
                        "description": "description",
                        "expires": "never",
                        "type": "string",
                        "version": 0,
                    },
                    {
                        "dates": {
                            "first": "2024-01-05 21:59:53",
                            "last": "2024-01-06 17:36:15",
                        },
                        "description": "description",
                        "expires": "never",
                        "type": "url",
                        "version": 0,
                    },
                ],
                "in-source": True,
                "name": "test.probe",
                "type": "string",
            }
        }

        with patch.object(glean, "get_dependencies", return_value=[]):
            with patch.object(
                glean,
                "_get_json",
                return_value=RETURN_VALUES,
            ):
                probes = glean.get_probes()
                assert len(probes) == 2
                assert probes[0].id == "test.probe"
                assert probes[0].type == "string"
                assert probes[1].id == "test.probe"
                assert probes[1].type == "url"

    # This test isn't technically a valid test since a schema glean-core would never be generated
    # independent of a define repo.  The expected value of bq_dataset_family has been updated to
    # reflect the new value that is assigned from the probe-scraper processing but is not be used
    # in a generated schema.
    def test_generic_schema(self, glean, config):
        schemas = glean.generate_schema(config, generic_schema=True)
        assert schemas.keys() == {
            "baseline",
            "events",
            "metrics",
            "deletion-request",
            "health",
        }

        final_schemas = {k: schemas[k].schema for k in schemas}
        for name, schema in final_schemas.items():
            generic_schema = glean.get_schema(generic_schema=True).schema
            generic_schema["mozPipelineMetadata"] = {
                "bq_dataset_family": "glean_core",
                "bq_metadata_format": "structured",
                "bq_table": name.replace("-", "_") + "_v1",
                "include_info_sections": True,
                "include_client_id": True,
            }
            print_and_test(generic_schema, schema)

    def test_missing_data(self, config):
        # When there are no files, this should error
        repo = {"name": "LeanGleanPingNoIding", "app_id": "org-mozilla-lean"}
        not_glean = NoProbeGleanPing(repo)
        with pytest.raises(requests.exceptions.HTTPError):
            not_glean.generate_schema(config)

    # Unit test covering the case where repository has a default expiration_policy and there is
    # also a ping specific expiration_policy.  The ping specific expiration_policy is applied to the
    # ping schema and the repository default expiration_policy is applied to the dependency ping
    # schema.
    @patch.object(glean_ping.GleanPing, "get_repos")
    def test_expiration_policy(self, mock_get_repos, config):
        mock_get_repos.return_value = [
            {
                "app_id": "app1",
                "dependencies": ["glean-base"],
                "moz_pipeline_metadata": {},
                "moz_pipeline_metadata_defaults": {
                    "bq_dataset_family": "app1",
                    "bq_metadata_format": "structured",
                    "expiration_policy": {
                        "delete_after_days": 20,
                        "collect_through_date": "2022-06-16",
                    },
                },
                "name": "app1",
            }
        ]
        glean = GleanPingWithExpirationPolicy({"name": "app1", "app_id": "app1"})
        schemas = glean.generate_schema(config, generic_schema=True)

        final_schemas = {k: schemas[k].schema for k in schemas}
        assert len(final_schemas) == 2
        for name, schema in final_schemas.items():
            if name == "ping1":
                assert (
                    schema["mozPipelineMetadata"]
                    == GleanPingWithExpirationPolicy.ping_metadata
                )
            if name == "dependency_ping":
                # Need to do individual comparison due to update of value based on app_id
                assert len(schema["mozPipelineMetadata"]) == 6
                assert schema["mozPipelineMetadata"]["bq_dataset_family"] == "app1"
                assert (
                    schema["mozPipelineMetadata"]["bq_metadata_format"] == "structured"
                )
                assert schema["mozPipelineMetadata"]["bq_table"] == "dependency_ping_v1"
                assert len(schema["mozPipelineMetadata"]["expiration_policy"]) == 2
                assert (
                    schema["mozPipelineMetadata"]["expiration_policy"][
                        "delete_after_days"
                    ]
                    == 20
                )
                assert (
                    schema["mozPipelineMetadata"]["expiration_policy"][
                        "collect_through_date"
                    ]
                    == "2022-06-16"
                )

    # Unit test covering the case where the repository has a default jwe_mappings and confirming
    # it is applied to all pings
    @patch.object(glean_ping.GleanPing, "get_repos")
    def test_jwe_mappings(self, mock_get_repos, config):
        mock_get_repos.return_value = [
            {
                "app_id": "app1",
                "dependencies": ["glean-base"],
                "moz_pipeline_metadata": {},
                "moz_pipeline_metadata_defaults": {
                    "bq_dataset_family": "app1",
                    "bq_metadata_format": "structured",
                    "jwe_mappings": [
                        {"decrypted_field_path": "", "source_field_path": "/payload"}
                    ],
                },
                "name": "app1",
            }
        ]
        glean = GleanPingWithEncryption({"name": "app1", "app_id": "app1"})
        schemas = glean.generate_schema(config, generic_schema=True)

        final_schemas = {k: schemas[k].schema for k in schemas}
        assert len(final_schemas) == 2
        for name, schema in final_schemas.items():
            if name == "ping1":
                assert (
                    schema["mozPipelineMetadata"]
                    == GleanPingWithEncryption.ping_metadata
                )
            if name == "dependency_ping":
                # Need to do individual comparison due to update of value based on app_id
                assert len(schema["mozPipelineMetadata"]) == 6
                assert schema["mozPipelineMetadata"]["bq_dataset_family"] == "app1"
                assert (
                    schema["mozPipelineMetadata"]["bq_metadata_format"] == "structured"
                )
                assert schema["mozPipelineMetadata"]["bq_table"] == "dependency_ping_v1"
                jwe_mappings = schema["mozPipelineMetadata"]["jwe_mappings"]
                assert jwe_mappings == GleanPingWithEncryption.ping_metadata.get(
                    "jwe_mappings"
                )

    # Note that even when the repo has no metadata defaults specified the glean/repositories
    # endpoint will add both bq_dataset_family and bq_metadata_format
    @patch.object(glean_ping.GleanPing, "get_repos")
    def test_no_metadata_defaults(self, mock_get_repos, config):
        mock_get_repos.return_value = [
            {
                "app_id": "app1",
                "dependencies": ["glean-base"],
                "moz_pipeline_metadata": {},
                "moz_pipeline_metadata_defaults": {
                    "bq_dataset_family": "app1",
                    "bq_metadata_format": "structured",
                },
                "name": "app1",
            }
        ]

        glean = GleanPingNoMetadata({"name": "app1", "app_id": "app1"})
        schemas = glean.generate_schema(config, generic_schema=True)
        final_schemas = {k: schemas[k].schema for k in schemas}

        assert len(final_schemas) == 2
        for name, schema in final_schemas.items():
            if name == "ping1":
                assert (
                    schema["mozPipelineMetadata"] == GleanPingNoMetadata.ping_metadata
                )
            if name == "dependency_ping":
                # Need to do individual comparison due to update of value based on app_id
                assert len(schema["mozPipelineMetadata"]) == 5
                assert schema["mozPipelineMetadata"]["bq_dataset_family"] == "app1"
                assert (
                    schema["mozPipelineMetadata"]["bq_metadata_format"] == "structured"
                )
                assert schema["mozPipelineMetadata"]["bq_table"] == "dependency_ping_v1"

    # Unit test covering the case where the repository has a default override_attributes
    # and confirming it is applied to all pings
    @patch.object(glean_ping.GleanPing, "get_repos")
    def test_override_attributes(self, mock_get_repos, config):
        mock_get_repos.return_value = [
            {
                "app_id": "app1",
                "dependencies": ["glean-base"],
                "moz_pipeline_metadata": {},
                "moz_pipeline_metadata_defaults": {
                    "bq_dataset_family": "app1",
                    "bq_metadata_format": "structured",
                    "override_attributes": [{"name": "geo_city", "value": None}],
                },
                "name": "app1",
            }
        ]
        glean = GleanPingWithOverrideAttributes({"name": "app1", "app_id": "app1"})
        schemas = glean.generate_schema(config, generic_schema=True)
        final_schemas = {k: schemas[k].schema for k in schemas}

        assert len(final_schemas) == 2
        for name, schema in final_schemas.items():
            if name == "ping1":
                assert (
                    schema["mozPipelineMetadata"]
                    == GleanPingWithOverrideAttributes.ping_metadata
                )
            if name == "dependency_ping":
                # Need to do individual comparison due to update of value based on app_id
                assert len(schema["mozPipelineMetadata"]) == 6
                assert schema["mozPipelineMetadata"]["bq_dataset_family"] == "app1"
                assert (
                    schema["mozPipelineMetadata"]["bq_metadata_format"] == "structured"
                )
                assert schema["mozPipelineMetadata"]["bq_table"] == "dependency_ping_v1"
                override_attr = schema["mozPipelineMetadata"]["override_attributes"]
                assert (
                    GleanPingWithOverrideAttributes.ping_metadata.get(
                        "override_attributes"
                    )
                    == override_attr
                )

    # Unit test covering the case where the repository has a default
    # submission_timestamp_granularity and confirming it is applied to all pings
    @patch.object(glean_ping.GleanPing, "get_repos")
    def test_submission_timestamp_granularity(self, mock_get_repos, config):
        mock_get_repos.return_value = [
            {
                "app_id": "app1",
                "dependencies": ["glean-base"],
                "moz_pipeline_metadata": {},
                "moz_pipeline_metadata_defaults": {
                    "bq_dataset_family": "app1",
                    "bq_metadata_format": "structured",
                    "submission_timestamp_granularity": "seconds",
                },
                "name": "app1",
            }
        ]

        glean = GleanPingWithGranularity({"name": "app1", "app_id": "app1"})
        schemas = glean.generate_schema(config, generic_schema=True)
        final_schemas = {k: schemas[k].schema for k in schemas}

        assert len(final_schemas) == 2
        for name, schema in final_schemas.items():
            if name == "ping1":
                assert (
                    schema["mozPipelineMetadata"]
                    == GleanPingWithGranularity.ping_metadata
                )
            if name == "dependency_ping":
                # Need to do individual comparison due to update of value based on app_id
                assert len(schema["mozPipelineMetadata"]) == 6
                assert schema["mozPipelineMetadata"]["bq_dataset_family"] == "app1"
                assert (
                    schema["mozPipelineMetadata"]["bq_metadata_format"] == "structured"
                )
                assert schema["mozPipelineMetadata"]["bq_table"] == "dependency_ping_v1"
                assert schema["mozPipelineMetadata"][
                    "submission_timestamp_granularity"
                ] == GleanPingWithGranularity.ping_metadata.get(
                    "submission_timestamp_granularity"
                )

    # Can reuse any other test class as long as the repo indicates there is no dependency (local
    # test config).
    @patch.object(glean_ping.GleanPing, "get_repos")
    def test_metadata_no_dependency(self, mock_get_repos, config):
        mock_get_repos.return_value = [
            {
                "app_id": "app1",
                "dependencies": [],
                "moz_pipeline_metadata": {},
                "moz_pipeline_metadata_defaults": {
                    "bq_dataset_family": "app1",
                    "bq_metadata_format": "structured",
                    "submission_timestamp_granularity": "seconds",
                },
                "name": "app1",
            }
        ]

        glean = GleanPingWithGranularity({"name": "app1", "app_id": "app1"})
        schemas = glean.generate_schema(config, generic_schema=True)
        final_schemas = {k: schemas[k].schema for k in schemas}

        assert len(final_schemas) == 1
        for name, schema in final_schemas.items():
            if name == "ping1":
                assert (
                    schema["mozPipelineMetadata"]
                    == GleanPingWithGranularity.ping_metadata
                )

    @patch.object(glean_ping.GleanPing, "get_repos")
    def test_ping_no_info_sections(self, mock_get_repos, config):
        mock_get_repos.return_value = [
            {
                "app_id": "app1",
                "dependencies": [],
                "moz_pipeline_metadata": {},
                "moz_pipeline_metadata_defaults": {
                    "bq_dataset_family": "app1",
                    "bq_metadata_format": "structured",
                },
                "name": "app1",
            }
        ]

        glean = GleanPingNoInfoSection(
            {"name": "app1", "app_id": "app1"},
        )
        schemas = glean.generate_schema(config, generic_schema=True)
        final_schemas = {k: schemas[k].schema for k in schemas}

        assert len(final_schemas) == 1
        for name, schema in final_schemas.items():
            assert "required" not in schema
            if name == "ping1":
                assert (
                    schema["mozPipelineMetadata"]
                    == GleanPingNoInfoSection.ping_metadata
                )

    @patch.object(glean_ping.GleanPing, "get_repos")
    def test_ping_no_info_sections_history(self, mock_get_repos, config):
        mock_get_repos.return_value = [
            {
                "app_id": "app1",
                "dependencies": [],
                "moz_pipeline_metadata": {},
                "moz_pipeline_metadata_defaults": {
                    "bq_dataset_family": "app1",
                    "bq_metadata_format": "structured",
                },
                "name": "app1",
            }
        ]

        glean = GleanPingNoInfoSectionWithHistory(
            {"name": "app1", "app_id": "app1"},
        )
        schemas = glean.generate_schema(config, generic_schema=True)
        final_schemas = {k: schemas[k].schema for k in schemas}

        assert len(final_schemas) == 1
        for name, schema in final_schemas.items():
            assert "required" not in schema
            if name == "ping1":
                assert (
                    schema["mozPipelineMetadata"]
                    == GleanPingNoInfoSectionWithHistory.ping_metadata
                )

    # Unit test covering case where 2 pings have specific metadata and default metadata is applied
    # to the dependency ping
    @patch.object(glean_ping.GleanPing, "get_repos")
    def test_metadata_multiple_pings(self, mock_get_repos, config):
        mock_get_repos.return_value = [
            {
                "app_id": "app1",
                "dependencies": ["glean-base"],
                "moz_pipeline_metadata": {
                    "ping1": GleanPingWithMultiplePings.ping1_metadata,
                    "ping2": GleanPingWithMultiplePings.ping2_metadata,
                },
                "moz_pipeline_metadata_defaults": {
                    "bq_dataset_family": "app1",
                    "bq_metadata_format": "structured",
                    "expiration_policy": {
                        "delete_after_days": 21,
                    },
                    "submission_timestamp_granularity": "seconds",
                },
                "name": "app1",
            }
        ]
        glean = GleanPingWithMultiplePings({"name": "app1", "app_id": "app1"})
        schemas = glean.generate_schema(config, generic_schema=True)
        final_schemas = {k: schemas[k].schema for k in schemas}

        assert len(final_schemas) == 3
        for name, schema in final_schemas.items():
            if name == "ping1":
                assert (
                    schema["mozPipelineMetadata"]
                    == GleanPingWithMultiplePings.ping1_metadata
                )
            if name == "ping2":
                assert (
                    schema["mozPipelineMetadata"]
                    == GleanPingWithMultiplePings.ping2_metadata
                )
            if name == "dependency_ping":
                # Need to do individual comparison due to update of value based on app_id
                assert len(schema["mozPipelineMetadata"]) == 7
                assert schema["mozPipelineMetadata"]["bq_dataset_family"] == "app1"
                assert (
                    schema["mozPipelineMetadata"]["bq_metadata_format"] == "structured"
                )
                assert schema["mozPipelineMetadata"]["bq_table"] == "dependency_ping_v1"
                assert (
                    schema["mozPipelineMetadata"]["expiration_policy"][
                        "delete_after_days"
                    ]
                    == 21
                )
                assert (
                    schema["mozPipelineMetadata"]["submission_timestamp_granularity"]
                    == "seconds"
                )

    # Integration test relies on ping, repositories and dependencies endpoints.
    def test_bug_1737656_unaffected(self, config):
        glean = glean_ping.GleanPing(
            {
                # This ping does not exist in the static list of affected pings.
                "name": "glean-core",
                "in-source": True,
                "app_id": "org-mozilla-glean",
            }
        )
        schemas = glean.generate_schema(config)

        final_schemas = {k: schemas[k].schema for k in schemas}
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
        schemas = glean.generate_schema(config)

        final_schemas = {k: schemas[k].schema for k in schemas}
        schema = final_schemas.get("metrics")
        assert "url" not in schema["properties"]["metrics"]["properties"].keys()
        assert "url2" in schema["properties"]["metrics"]["properties"].keys()
        assert list(
            (schema["properties"]["metrics"]["properties"]["url2"]["properties"].keys())
        ) == ["my_url"]

    def test_override_nested_defaults(self, config):
        """
        We want to test that any defaults set in the schema
        get applied to the generated schema here,
        while also applying any defaults from here.

        Notably we now set `json_object_path_regex` for all Glean schemas.
        """

        # Patching GenericPing.get_schema to return the schema
        # that will contain the configuration soon.
        # This should continue to work
        # even if the upstream schema actually gains those fields.
        json = generic_ping.GenericPing._get_json(
            glean_ping.DEFAULT_SCHEMA_URL.format(branch="main")
        )
        json.update(
            {
                "mozPipelineMetadata": {
                    "json_object_path_regex": "metrics\\.object\\..*",
                }
            }
        )
        with patch.object(
            generic_ping.GenericPing, "get_schema", return_value=Schema(json)
        ):
            glean = glean_ping.GleanPing(
                {"name": "glean-core", "app_id": "org-mozilla-glean"}
            )
            schemas = glean.generate_schema(config)
            final_schemas = {k: schemas[k].schema for k in schemas}

            # Glean built-in pings only.
            assert len(final_schemas) == 5

            expected_metdata = {
                "bq_dataset_family": "glean_core",
                "bq_table": "metrics_v1",
                "bq_metadata_format": "structured",
                "json_object_path_regex": "metrics\\.object\\..*",
                "include_info_sections": True,
                "include_client_id": True,
            }
            for name, schema in final_schemas.items():
                if name == "metrics":
                    assert schema["mozPipelineMetadata"] == expected_metdata

    def test_override_dependency_metadata(self, config):
        glean = GleanPingWithMetadataOverrides({"name": "app1", "app_id": "app1"})

        pings = glean._get_ping_data_and_dependencies_with_default_metadata()

        expected_pings = {
            **glean._get_ping_data_without_dependencies(),
            **glean._get_dependency_pings(""),
        }
        expected_pings["dependency_ping1"]["moz_pipeline_metadata"][
            "expiration_policy"
        ] = {"delete_after_days": 80}
        expected_pings["dependency_ping2"]["moz_pipeline_metadata"][
            "expiration_policy"
        ] = {"delete_after_days": 90}
        expected_pings["dependency_ping3"]["moz_pipeline_metadata"][
            "expiration_policy"
        ] = {"delete_after_days": 100}
        expected_pings["dependency_ping3"]["moz_pipeline_metadata"][
            "override_attributes"
        ] = [{"name": "geo_city", "value": None}]

        assert pings == expected_pings
