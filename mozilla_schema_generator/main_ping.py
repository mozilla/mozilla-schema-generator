# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
from .generic_ping import GenericPing
from .schema import Schema
from .probes import MainProbe
from typing import List


class MainPing(GenericPing):

    schema_url = "https://raw.githubusercontent.com/mozilla-services/mozilla-pipeline-schemas/dev/schemas/telemetry/main/main.4.schema.json" # noqa E501
    env_url = "https://raw.githubusercontent.com/mozilla-services/mozilla-pipeline-schemas/dev/templates/include/telemetry/environment.1.schema.json" # noqa E501
    probes_url = "https://probeinfo.telemetry.mozilla.org/firefox/all/main/all_probes"

    def __init__(self):
        super().__init__(self.schema_url, self.env_url, self.probes_url)

    def get_schema(self):
        schema = super().get_schema()

        # 1. add item to range
        range_type = {"type": "integer"}
        schema.set_schema_elem(("properties", "payload", "properties", "histograms", "additionalProperties", "properties", "range", "items"), range_type) # noqa E501
        schema.set_schema_elem(("properties", "payload", "properties", "keyedHistograms", "additionalProperties", "additionalProperties", "properties", "range", "items"), range_type) # noqa E501
        for p in ("parent", "content", "gpu"):
            schema.set_schema_elem(("properties", "payload", "properties", "processes", "properties", p, "properties", "histograms", "additionalProperties", "properties", "range", "items"), range_type) # noqa E501
            schema.set_schema_elem(("properties", "payload", "properties", "processes", "properties", p, "properties", "keyedHistograms", "additionalProperties", "additionalProperties", "properties", "range", "items"), range_type) # noqa E501

        # 3. Add items defn to UIMeasurements
        schema.set_schema_elem(
            ("properties", "payload", "properties", "UIMeasurements", "items"),
            {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "action": {"type": "string"},
                    "method": {"type": "string"},
                    "extras": {"type": "string"},
                    "timestamp": {"type": "number"},
                },
                "additionalProperties": False
            })

        # 4. Ignore childPayloads, deprecated in 61
        schema._delete_key(("properties", "payload", "properties", "childPayloads"))

        # 5. Ignore log, deprecated in 61
        schema._delete_key(("properties", "payload", "properties", "log"))

        # 6. Update slices
        for p in ("parent", "content", "gpu"):
            schema.set_schema_elem(("properties", "payload", "properties", "processes", "properties", p, "properties", "gc", "properties", "random", "items", "properties", "slices", "type"), "number") # noqa E501
            schema.set_schema_elem(("properties", "payload", "properties", "processes", "properties", p, "properties", "gc", "properties", "worst", "items", "properties", "slices", "type"), "number") # noqa E501

        # 7. Ignore threadHangStats, deprecated in 57
        schema._delete_key(("properties", "payload", "properties", "threadHangStats"))

        return self._update_env(schema)

    def _update_env(self, schema):
        # 2. Make partnerNames just a str array
        schema.set_schema_elem(("properties", "environment", "properties", "partner", "properties", "partnerNames", "type"), "array") # noqa E501
        schema.set_schema_elem(("properties", "environment", "properties", "partner", "properties", "partnerNames", "items"), {"type": "string"}) # noqa E501
        return schema

    def get_env(self):
        env_property = json.loads("{" + self._get_json_str(self.env_url) + "}")
        env = {
            "type": "object",
            "properties": env_property
        }

        return self._update_env(Schema(env))

    def get_probes(self) -> List[MainProbe]:
        probes = self._get_json(self.probes_url)

        for name, defn in probes.items():
            history = [d for arr in defn["history"].values() for d in arr]
            defn["history"] = sorted(history, key=lambda x: int(x["versions"]["first"]),
                                     reverse=True)

        filtered = {
            pname: pdef for pname, pdef in probes.items()
            if "nightly" in pdef["first_added"]
        }

        return [MainProbe(_id, defn) for _id, defn in filtered.items()]
