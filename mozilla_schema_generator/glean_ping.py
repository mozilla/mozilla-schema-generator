# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from requests import HTTPError

from .config import Config
from .generic_ping import GenericPing
from .probes import GleanProbe
from .schema import Schema
from typing import Dict, List, Set


logger = logging.getLogger(__name__)


class GleanPing(GenericPing):

    schema_url = "https://raw.githubusercontent.com/mozilla-services/mozilla-pipeline-schemas/master/schemas/glean/glean/glean.1.schema.json" # noqa E501
    probes_url_template = "https://probeinfo.telemetry.mozilla.org/glean/{}/metrics"
    ping_url_template = "https://probeinfo.telemetry.mozilla.org/glean/{}/pings"
    repos_url = "https://probeinfo.telemetry.mozilla.org/glean/repositories"
    dependencies_url_template = "https://probeinfo.telemetry.mozilla.org/glean/{}/dependencies"

    default_dependencies = ['glean']
    default_pings = {"baseline", "events", "metrics", "deletion-request"}
    ignore_pings = {"all-pings", "all_pings", "default", "glean_ping_info", "glean_client_info"}

    def __init__(self, repo):  # TODO: Make env-url optional
        self.repo = repo
        super().__init__(
            self.schema_url,
            self.schema_url,
            self.probes_url_template.format(repo)
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
            for library_name in repo.get('library_names', []):
                repos_by_dependency_name[library_name] = repo['name']

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

        return [GleanProbe(_id, defn, pings=pings) for _id, defn in probes]

    def get_pings(self) -> Set[str]:
        try:
            url = self.ping_url_template.format(self.repo)
            pings = GleanPing._get_json(url)
            addl_pings = set(pings.keys())

            return self.default_pings | addl_pings
        except HTTPError:
            # If we get an error (e.g. 404 Not Found) we fall back to only the default pings
            return self.default_pings

    def generate_schema(self, config, split, generic_schema=False) -> Dict[str, List[Schema]]:
        pings = self.get_pings()
        schemas = {}

        for ping in pings:
            matchers = {loc: m.clone(new_table_group=ping) for loc, m in config.matchers.items()}
            for matcher in matchers.values():
                matcher.matcher["send_in_pings"]["contains"] = ping
            new_config = Config(ping, matchers=matchers)

            if generic_schema:  # Use the generic glean ping schema
                schemas[new_config.name] = [self.get_schema()]
            else:
                schemas.update(super().generate_schema(new_config))

        return schemas

    @staticmethod
    def get_repos():
        """
        Retrieve name and app_id for Glean repositories
        """
        repos = GleanPing._get_json(GleanPing.repos_url)
        return [(repo['name'], repo['app_id']) for repo in repos if 'library_names' not in repo]
