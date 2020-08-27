# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
from .generic_ping import GenericPing
from .schema import Schema
from .probes import MainProbe
from .utils import prepend_properties, property_exists
from typing import List


class CommonPing(GenericPing):

    # Only includes probes that have been available at some point past
    # this version.
    # ONLY DECREMENT, or the schema will change in an incompatible way!
    MIN_FX_VERSION = 30

    env_url = "https://raw.githubusercontent.com/mozilla-services/mozilla-pipeline-schemas/master/templates/include/telemetry/environment.1.schema.json" # noqa E501
    probes_url = GenericPing.probe_info_base_url + "/firefox/all/main/all_probes"

    def __init__(self, schema_url):
        super().__init__(schema_url, self.env_url, self.probes_url)

    def get_schema(self):
        schema = super().get_schema()

        try:
            schema.get(prepend_properties(("environment",)))
            return self._update_env(schema)
        except KeyError:
            return schema

    def _update_env(self, schema):
        integer = {"type": "integer"}
        string = {"type": "string"}
        string_map = {
            "type": "object",
            "additionalProperties": string,
        }
        boolean = {"type": "boolean"}

        def with_description(dtype: dict, comment: str) -> dict:
            """Add a description to the types defined above."""
            return {**dtype, **dict(description=comment)}

        active_addons = prepend_properties(("environment", "addons", "activeAddons")) \
            + ("additionalProperties", "properties")

        # If active_addons doesn't exist in the schema, then this is a simplified
        # environment and we can skip the below modifications.
        if property_exists(schema.schema, active_addons):
            schema.set_schema_elem(
                prepend_properties(("environment", "settings", "userPrefs")),
                with_description(
                    string_map,
                    "User preferences - limited to an allowlist defined in "
                    "`toolkit/components/telemetry/app/TelemetryEnvironment.jsm`",
                ),
            )
            schema.set_schema_elem(
                    prepend_properties(("environment", "system", "os", "version")), string)
            schema.set_schema_elem(
                    prepend_properties(("environment", "system", "os", "hasSuperfetch")), boolean)
            schema.set_schema_elem(
                    prepend_properties(("environment", "system", "os", "hasPrefetch")), boolean)
            schema.set_schema_elem(
                    prepend_properties(("environment", "addons", "theme", "foreignInstall")),
                    integer)
            schema.set_schema_elem(active_addons + ("foreignInstall",), integer)
            schema.set_schema_elem(active_addons + ("version",), string)
            schema.set_schema_elem(active_addons + ("userDisabled",), integer)
            schema.set_schema_elem(
                prepend_properties(("environment", "addons", "activeGMPlugins"))
                + ("additionalProperties", "properties", "applyBackgroundUpdates"),
                with_description(
                    integer,
                    "Cast into an integer via mozilla-schema-generator. See bug 1611027.",
                ),
            )

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
