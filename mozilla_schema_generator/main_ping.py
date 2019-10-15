# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
from .generic_ping import GenericPing
from .schema import Schema
from .probes import MainProbe
from .utils import prepend_properties
from typing import List


class MainPing(GenericPing):

    # Only includes probes that have been available at some point past
    # this version.
    # ONLY DECREMENT, or the schema will change in an incompatible way!
    MIN_FX_VERSION = 30

    schema_url = "https://raw.githubusercontent.com/mozilla-services/mozilla-pipeline-schemas/master/schemas/telemetry/main/main.4.schema.json" # noqa E501
    env_url = "https://raw.githubusercontent.com/mozilla-services/mozilla-pipeline-schemas/master/templates/include/telemetry/environment.1.schema.json" # noqa E501
    probes_url = "https://probeinfo.telemetry.mozilla.org/firefox/all/main/all_probes"

    def __init__(self):
        super().__init__(self.schema_url, self.env_url, self.probes_url)

    def get_schema(self):
        schema = super().get_schema()
        return self._update_env(schema)

    def _update_env(self, schema):
        user_pref_elem = {
            "type": "object",
            "additionalProperties": {
                "type": "string"
            }
        }

        schema.set_schema_elem(
                prepend_properties(("environment", "settings", "userPrefs")), user_pref_elem)
        schema.set_schema_elem(
                prepend_properties(("environment", "system", "os", "version")), {"type": "string"})
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

        filtered = {
            pname: pdef for pname, pdef in probes.items()
            if "nightly" in pdef["first_added"]
        }

        # This will be made much better with PEP 572
        main_probes = [MainProbe(_id, defn) for _id, defn in filtered.items()]
        return [p for p in main_probes
                if int(p.definition["versions"]["last"]) > self.MIN_FX_VERSION]
