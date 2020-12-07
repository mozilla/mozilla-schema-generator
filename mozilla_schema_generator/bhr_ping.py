# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from .common_ping import CommonPing
from .utils import prepend_properties


class BhrPing(CommonPing):
    schema_url = (
        "https://raw.githubusercontent.com/mozilla-services/mozilla-pipeline-schemas"
        "/{branch}/schemas/telemetry/bhr/bhr.4.schema.json"
    )

    def __init__(self, **kwargs):
        super().__init__(self.schema_url, **kwargs)

    def _update_env(self, schema):
        # hangs is an array of objects
        stack = prepend_properties(("payload", "hangs")) + (
            "items",
            "properties",
            "stack",
        )
        schema.set_schema_elem(
            stack,
            {
                "type": "string",
                "description": (
                    "JSON representation of the stack field."
                    " Injected by mozilla-schema-generator."
                ),
            },
            # this may otherwise overwrite the "items" fields
            propagate=False,
        )

        return super()._update_env(schema)
