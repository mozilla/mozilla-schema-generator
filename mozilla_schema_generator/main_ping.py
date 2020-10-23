# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from .common_ping import CommonPing
from .utils import prepend_properties


class MainPing(CommonPing):
    schema_url = (
        "https://raw.githubusercontent.com/mozilla-services/mozilla-pipeline-schemas"
        "/{branch}/schemas/telemetry/main/main.4.schema.json"
    )

    def __init__(self, **kwargs):
        super().__init__(self.schema_url, **kwargs)

    def _update_env(self, schema):
        integer = {"type": "integer"}
        simple_measurements = prepend_properties(("payload", "simpleMeasurements", ""))[
            :-1
        ]

        schema.set_schema_elem(simple_measurements + ("activeTicks",), integer)
        schema.set_schema_elem(simple_measurements + ("blankWindowShown",), integer)
        schema.set_schema_elem(simple_measurements + ("firstPaint",), integer)
        schema.set_schema_elem(simple_measurements + ("main",), integer)
        schema.set_schema_elem(simple_measurements + ("sessionRestored",), integer)
        schema.set_schema_elem(simple_measurements + ("totalTime",), integer)

        return super()._update_env(schema)
