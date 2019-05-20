# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from .config import Config
from .generic_ping import GenericPing
from .probes import GleanProbe
from typing import List


class GleanPing(GenericPing):

    schema_url = "https://raw.githubusercontent.com/mozilla-services/mozilla-pipeline-schemas/dev/schemas/glean/baseline/baseline.1.schema.json" # noqa E501
    probes_url_template = "https://probeinfo.telemetry.mozilla.org/glean/{}/metrics"
    repos_url = "https://probeinfo.telemetry.mozilla.org/glean/repositories"

    default_dependencies = ['glean']
    default_pings = {"baseline", "events", "metrics"}
    ignore_pings = {"default", "glean_ping_info", "glean_client_info"}

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

        dependencies = self._get_json(self.dependencies_url.format(self.repo))
        dependency_library_names = list(dependencies.keys())

        repos = self.get_repos()
        repos_by_dependency_name = {}
        for repo in repos:
            for library_name in repo.get('library_names', []):
                repos_by_dependency_name[library_name] = repo

        dependencies = []
        for name in dependency_library_names:
            if name in repos_by_dependency_name:
                dependencies.append(repos_by_dependency_name[name])

        if not len(dependencies):
            return self.default_dependencies

        return dependencies

    def get_probes(self) -> List[GleanProbe]:
        probes = self._get_json(self.probes_url)
        items = list(probes.items())
        for dependency in self.get_dependencies():
            dependency_probes = self._get_json(
                self.probes_url_template.format(dependency)
            )
            items += list(dependency_probes.items())

        return [GleanProbe(_id, defn) for _id, defn in items]

    def get_pings(self):
        probes = self.get_probes()
        addl_pings = {
            ping for probe in probes
            for ping in probe.definition["send_in_pings"]
            if ping not in self.ignore_pings
        }

        return self.default_pings | addl_pings

    def generate_schema(self, config, split):
        pings = self.get_pings()
        schemas = {}

        for ping in pings:
            matchers = {loc: m.clone(new_table_group=ping) for loc, m in config.matchers.items()}
            for matcher in matchers.values():
                matcher.matcher["send_in_pings"]["contains"] = ping
            new_config = Config(ping, matchers=matchers)

            schemas.update(super().generate_schema(new_config))

        return schemas

    @staticmethod
    def get_repos():
        """
        Retrieve name and app_id for Glean repositories
        """
        repos = GleanPing._get_json(GleanPing.repos_url)
        return [(repo['name'], repo['app_id']) for repo in repos]
