# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
from typing import Dict, List, Set

from requests import HTTPError

from .config import Config
from .generic_ping import GenericPing
from .probes import GleanProbe
from .schema import Schema

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

    default_dependencies = ["glean"]
    ignore_pings = {
        "all-pings",
        "all_pings",
        "default",
        "glean_ping_info",
        "glean_client_info",
    }

    def __init__(self, repo, app_id, **kwargs):  # TODO: Make env-url optional
        self.repo = repo
        self.app_id = app_id
        super().__init__(
            self.schema_url,
            self.schema_url,
            self.probes_url_template.format(repo),
            **kwargs,
        )

    def get_dependencies(self):
        # Get all of the library dependencies for the application that
        # are also known about in the repositories file.

        # The dependencies are specified using library names, but we need to
        # map those back to the name of the repository in the repository file.
        try:
            dependencies = self._get_json(
                self.dependencies_url_template.format(self.repo)
            )
        except HTTPError:
            logging.info(f"For {self.repo}, using default Glean dependencies")
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
            logging.info(f"For {self.repo}, using default Glean dependencies")
            return self.default_dependencies

        logging.info(f"For {self.repo}, found Glean dependencies: {dependencies}")
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
                self.repo in issue_118_affected
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

    def get_pings(self) -> Set[str]:
        url = self.ping_url_template.format(self.repo)
        pings = GleanPing._get_json(url).keys()

        for dependency in self.get_dependencies():
            dependency_pings = self._get_json(self.ping_url_template.format(dependency))
            pings |= dependency_pings.keys()

        return pings

    def generate_schema(
        self, config, split, generic_schema=False
    ) -> Dict[str, List[Schema]]:
        pings = self.get_pings()
        schemas = {}

        for ping in pings:
            matchers = {
                loc: m.clone(new_table_group=ping) for loc, m in config.matchers.items()
            }
            for matcher in matchers.values():
                matcher.matcher["send_in_pings"]["contains"] = ping
            new_config = Config(ping, matchers=matchers)

            defaults = {
                "mozPipelineMetadata": {
                    "bq_dataset_family": self.app_id.replace("-", "_"),
                    "bq_table": ping.replace("-", "_") + "_v1",
                    "bq_metadata_format": "structured",
                }
            }

            if generic_schema:  # Use the generic glean ping schema
                schema = self.get_schema()
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
        Retrieve name and app_id for Glean repositories
        """
        repos = GleanPing._get_json(GleanPing.repos_url)
        return [
            (repo["name"], repo["app_id"])
            for repo in repos
            if "library_names" not in repo
        ]
