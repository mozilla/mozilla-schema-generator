# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
from pathlib import Path
from typing import Dict, List, Set

from requests import HTTPError

from .config import Config
from .generic_ping import GenericPing
from .probes import GleanProbe
from .schema import Schema

ROOT_DIR = Path(__file__).parent
BUG_1737656_TXT = ROOT_DIR / "configs" / "bug_1737656_affected.txt"

logger = logging.getLogger(__name__)


class GleanPing(GenericPing):
    schema_url = (
        "https://raw.githubusercontent.com/mozilla-services/mozilla-pipeline-schemas"
        "/{branch}/schemas/glean/glean/glean.1.schema.json"
    )
    probes_url_template = GenericPing.probe_info_base_url + "/glean/{}/metrics"
    ping_url_template = GenericPing.probe_info_base_url + "/glean/{}/pings"
    repos_url = GenericPing.probe_info_base_url + "/glean/repositories"
    dependencies_url_template = (
        GenericPing.probe_info_base_url + "/glean/{}/dependencies"
    )

    default_dependencies = ["glean-core"]
    ignore_pings = {
        "all-pings",
        "all_pings",
        "default",
        "glean_ping_info",
        "glean_client_info",
    }

    with open(BUG_1737656_TXT, "r") as f:
        bug_1737656_affected_tables = [
            line.strip() for line in f.readlines() if line.strip()
        ]

    def __init__(self, repo, **kwargs):  # TODO: Make env-url optional
        self.repo = repo
        self.repo_name = repo["name"]
        self.app_id = repo["app_id"]
        super().__init__(
            self.schema_url,
            self.schema_url,
            self.probes_url_template.format(self.repo_name),
            **kwargs,
        )

    def get_schema(self, generic_schema=False) -> Schema:
        """
        Fetch schema via URL.

        Unless *generic_schema* is set to true, this function makes some modifications
        to allow some workarounds for proper injection of metrics.
        """
        schema = super().get_schema()
        if generic_schema:
            return schema

        # We need to inject placeholders for the url2, text2, etc. types as part
        # of mitigation for https://bugzilla.mozilla.org/show_bug.cgi?id=1737656
        for metric_name in ["labeled_rate", "jwe", "url", "text"]:
            metric1 = schema.get(
                ("properties", "metrics", "properties", metric_name)
            ).copy()
            metric1 = schema.set_schema_elem(
                ("properties", "metrics", "properties", metric_name + "2"),
                metric1,
            )

        return schema

    def get_dependencies(self):
        # Get all of the library dependencies for the application that
        # are also known about in the repositories file.

        # The dependencies are specified using library names, but we need to
        # map those back to the name of the repository in the repository file.
        try:
            dependencies = self._get_json(
                self.dependencies_url_template.format(self.repo_name)
            )
        except HTTPError:
            logging.info(f"For {self.repo_name}, using default Glean dependencies")
            return self.default_dependencies

        dependency_library_names = list(dependencies.keys())

        repos = GleanPing._get_json(GleanPing.repos_url)
        repos_by_dependency_name = {}
        for repo in repos:
            for library_name in repo.get("library_names", []):
                repos_by_dependency_name[library_name] = repo["name"]

        dependencies = []
        for name in dependency_library_names:
            if name in repos_by_dependency_name:
                dependencies.append(repos_by_dependency_name[name])

        if len(dependencies) == 0:
            logging.info(f"For {self.repo_name}, using default Glean dependencies")
            return self.default_dependencies

        logging.info(f"For {self.repo_name}, found Glean dependencies: {dependencies}")
        return dependencies

    def get_probes(self) -> List[GleanProbe]:
        data = self._get_json(self.probes_url)
        probes = list(data.items())

        for dependency in self.get_dependencies():
            dependency_probes = self._get_json(
                self.probes_url_template.format(dependency)
            )
            probes += list(dependency_probes.items())

        pings = self.get_pings()

        processed = []
        for _id, defn in probes:
            probe = GleanProbe(_id, defn, pings=pings)
            processed.append(probe)

            # Manual handling of incompatible schema changes
            issue_118_affected = {
                "fenix",
                "fenix-nightly",
                "firefox-android-nightly",
                "firefox-android-beta",
                "firefox-android-release",
            }
            if (
                self.repo_name in issue_118_affected
                and probe.get_name() == "installation.timestamp"
            ):
                logging.info(f"Writing column {probe.get_name()} for compatibility.")
                # See: https://github.com/mozilla/mozilla-schema-generator/issues/118
                # Search through history for the "string" type and add a copy of
                # the probe at that time in history. The changepoint signifies
                # this event.
                changepoint_index = 0
                for definition in probe.definition_history:
                    if definition["type"] != probe.get_type():
                        break
                    changepoint_index += 1
                # Modify the definition with the truncated history.
                hist_defn = defn.copy()
                hist_defn[probe.history_key] = probe.definition_history[
                    changepoint_index:
                ]
                hist_defn["type"] = hist_defn[probe.history_key][0]["type"]
                incompatible_probe_type = GleanProbe(_id, hist_defn, pings=pings)
                processed.append(incompatible_probe_type)

        return processed

    def _get_ping_data(self) -> Dict[str, Dict]:
        url = self.ping_url_template.format(self.repo_name)
        ping_data = GleanPing._get_json(url)
        for dependency in self.get_dependencies():
            dependency_pings = self._get_json(self.ping_url_template.format(dependency))
            ping_data.update(dependency_pings)
        return ping_data

    def _get_ping_data_without_dependencies(self) -> Dict[str, Dict]:
        url = self.ping_url_template.format(self.repo_name)
        ping_data = GleanPing._get_json(url)
        return ping_data

    def _get_dependency_pings(self, dependency):
        return self._get_json(self.ping_url_template.format(dependency))

    def get_pings(self) -> Set[str]:
        return self._get_ping_data().keys()

    @staticmethod
    def apply_default_metadata(ping_metadata, default_metadata):
        """apply_default_metadata recurses down into dicts nested
        to an arbitrary depth, updating keys. The ``default_metadata`` is merged into
        ``ping_metadata``.
        :param ping_metadata: dict onto which the merge is executed
        :param default_metadata: dct merged into ping_metadata
        :return: None
        """
        for k, v in default_metadata.items():
            if (
                k in ping_metadata
                and isinstance(ping_metadata[k], dict)
                and isinstance(default_metadata[k], dict)
            ):
                GleanPing.apply_default_metadata(ping_metadata[k], default_metadata[k])
            else:
                ping_metadata[k] = default_metadata[k]

    def _get_ping_data_and_dependencies_with_default_metadata(self) -> Dict[str, Dict]:
        # Get the ping data with the pipeline metadata
        ping_data = self._get_ping_data_without_dependencies()

        # The ping endpoint for the dependency pings does not include any repo defined
        # moz_pipeline_metadata_defaults so they need to be applied here.

        # 1.  Get repo and pipeline default metadata.
        repos = GleanPing.get_repos()
        current_repo = next((x for x in repos if x.get("app_id") == self.app_id), {})
        default_metadata = current_repo.get("moz_pipeline_metadata_defaults", {})

        # 2.  Apply the default metadata to each dependency defined ping.
        for dependency in self.get_dependencies():
            dependency_pings = self._get_dependency_pings(dependency)
            for dependency_ping in dependency_pings.values():
                # Although it is counter intuitive to apply the default metadata on top of the
                # existing dependency ping metadata it does set the repo specific value for
                # bq_dataset_family instead of using the dependency id for the bq_dataset_family
                # value.
                GleanPing.apply_default_metadata(
                    dependency_ping.get("moz_pipeline_metadata"), default_metadata
                )
            ping_data.update(dependency_pings)
        return ping_data

    @staticmethod
    def reorder_metadata(metadata):
        desired_order_list = [
            "bq_dataset_family",
            "bq_table",
            "bq_metadata_format",
            "submission_timestamp_granularity",
            "expiration_policy",
            "override_attributes",
            "jwe_mappings",
        ]
        reordered_metadata = {
            k: metadata[k] for k in desired_order_list if k in metadata
        }

        # re-order jwe-mappings
        desired_order_list = ["source_field_path", "decrypted_field_path"]
        jwe_mapping_metadata = reordered_metadata.get("jwe_mappings")
        if jwe_mapping_metadata:
            reordered_jwe_mapping_metadata = []
            for mapping in jwe_mapping_metadata:
                reordered_jwe_mapping_metadata.append(
                    {k: mapping[k] for k in desired_order_list if k in mapping}
                )
            reordered_metadata["jwe_mappings"] = reordered_jwe_mapping_metadata

        # future proofing, in case there are other fields added at the ping top level
        # add them to the end.
        leftovers = {k: metadata[k] for k in set(metadata) - set(reordered_metadata)}
        reordered_metadata = {**reordered_metadata, **leftovers}
        return reordered_metadata

    def get_pings_and_pipeline_metadata(self) -> Dict[str, Dict]:
        pings = self._get_ping_data_and_dependencies_with_default_metadata()
        for ping_name, ping_data in pings.items():
            metadata = ping_data.get("moz_pipeline_metadata")

            # While technically unnecessary, the dictionary elements are re-ordered to match the
            # currently deployed order and used to verify no difference in output.
            pings[ping_name] = GleanPing.reorder_metadata(metadata)
        return pings

    def get_ping_descriptions(self) -> Dict[str, str]:
        return {
            k: v["history"][-1]["description"] for k, v in self._get_ping_data().items()
        }

    def generate_schema(
        self, config, split, generic_schema=False
    ) -> Dict[str, List[Schema]]:
        pings = self.get_pings_and_pipeline_metadata()
        schemas = {}

        for ping, pipeline_meta in pings.items():
            matchers = {
                loc: m.clone(new_table_group=ping) for loc, m in config.matchers.items()
            }

            # Four newly introduced metric types were incorrectly deployed
            # as repeated key/value structs in all Glean ping tables existing prior
            # to November 2021. We maintain the incorrect fields for existing tables
            # by disabling the associated matchers.
            # Note that each of these types now has a "2" matcher ("text2", "url2", etc.)
            # defined that will allow metrics of these types to be injected into proper
            # structs. The gcp-ingestion repository includes logic to rewrite these
            # metrics under the "2" names.
            # See https://bugzilla.mozilla.org/show_bug.cgi?id=1737656
            bq_identifier = "{bq_dataset_family}.{bq_table}".format(**pipeline_meta)
            if bq_identifier in self.bug_1737656_affected_tables:
                matchers = {
                    loc: m
                    for loc, m in matchers.items()
                    if not m.matcher.get("bug_1737656_affected")
                }

            for matcher in matchers.values():
                matcher.matcher["send_in_pings"]["contains"] = ping
            new_config = Config(ping, matchers=matchers)

            defaults = {"mozPipelineMetadata": pipeline_meta}

            if generic_schema:  # Use the generic glean ping schema
                schema = self.get_schema(generic_schema=True)
                schema.schema.update(defaults)
                schemas[new_config.name] = [schema]
            else:
                generated = super().generate_schema(new_config)
                for value in generated.values():
                    for schema in value:
                        schema.schema.update(defaults)
                schemas.update(generated)

        return schemas

    @staticmethod
    def get_repos():
        """
        Retrieve metadata for all non-library Glean repositories
        """
        repos = GleanPing._get_json(GleanPing.repos_url)
        return [repo for repo in repos if "library_names" not in repo]
