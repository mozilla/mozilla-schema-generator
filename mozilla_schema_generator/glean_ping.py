# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from .probes import GleanProbe
from .generic_ping import GenericPing
from .schema import Schema
from typing import List


class GleanPing(GenericPing):

    schema_url = "https://raw.githubusercontent.com/mozilla-services/mozilla-pipeline-schemas/dev/schemas/glean/baseline/baseline.1.schema.json" # noqa E501
    probes_url = "https://probeinfo.telemetry.mozilla.org/glean/glean/metrics"

    def __init__(self):  # TODO: Make env-url optional
        super().__init__(self.schema_url, self.schema_url, self.probes_url)

    def get_schema(self) -> Schema:
        return self._get_schema()

    def get_env(self) -> Schema:
        return self._get_schema()

    def _get_schema(self) -> Schema:
        schema = super().get_schema()

        # 1. Set the $schema to a string type
        schema.set_schema_elem(
            ("properties", "$schema", "type"),
            "string"
        )

        # 2. Set the metrics to an object type
        schema.set_schema_elem(
            ("properties", "metrics", "type"),
            "object"
        )

        # 3. Set the experiments to an object type
        schema.set_schema_elem(
            ("properties", "ping_info", "properties", "experiments", "type"),
            "object"
        )

        return schema

    def get_probes(self) -> List[GleanProbe]:
        probes = self._get_json(self.probes_url)
        return [GleanProbe(_id, defn) for _id, defn in probes.items()]
