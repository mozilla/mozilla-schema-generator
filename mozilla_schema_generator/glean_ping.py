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
    probes_url = "https://probeinfo.telemetry.mozilla.org/glean/{}/metrics"
    repos_url = "https://probeinfo.telemetry.mozilla.org/glean/repositories"

    default_probes_url = probes_url.format("glean")
    default_pings = {"baseline", "event", "metrics"}
    ignore_pings = {"default", "glean_ping_info", "glean_client_info"}

    def __init__(self, repo):  # TODO: Make env-url optional
        super().__init__(self.schema_url, self.schema_url, self.probes_url.format(repo))

    def get_probes(self) -> List[GleanProbe]:
        probes = self._get_json(self.probes_url)
        default_probes = self._get_json(self.default_probes_url)
        items = list(probes.items()) + list(default_probes.items())

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
