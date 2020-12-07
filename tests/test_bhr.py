# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from mozilla_schema_generator.bhr_ping import BhrPing
from mozilla_schema_generator.config import Config


def test_schema_contains_hangs_stacks():
    schema = BhrPing().generate_schema(Config("bhr", {}))["bhr"][0].schema
    hangs = schema["properties"]["payload"]["properties"]["hangs"]
    assert hangs["items"]["properties"]["stack"]["type"] == "string"
