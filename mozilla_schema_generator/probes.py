# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


from __future__ import annotations

from datetime import datetime
from typing import Any, List
from .utils import _get
from .schema import SchemaException


class Probe(object):

    type_key = "type"
    name_key = "name"
    history_key = "history"

    def __init__(self, identifier: str, definition: dict):
        self.id = identifier
        self.type = definition[self.type_key]
        self.name = definition[self.name_key]

    def get_type(self) -> str:
        return self.type

    def get_name(self) -> str:
        return self.name

    def get_last_change(self) -> datetime:
        raise NotImplementedError("Last Change is not available on generic probe")

    def get_first_added(self) -> datetime:
        raise NotImplementedError("First added is not available on generic probe")

    def get_schema(self, addtlProps: Any) -> Any:
        raise NotImplementedError("Get Schema is not available on generic probe")

    def get(self, *k) -> Any:
        return _get(self.definition, k)

    def __lt__(self, other: Probe) -> bool:
        if self.get_first_added() == other.get_first_added():
            return self.get_name() < other.get_name()

        return self.get_first_added() < other.get_first_added()


class MainProbe(Probe):

    first_added_key = "first_added"

    histogram_schema = {
        "type": "string",
    }

    def __init__(self, identifier: str, definition: dict):
        self._set_dates(definition[self.first_added_key])
        self._set_definition(definition)
        super().__init__(identifier, definition)

    def _set_definition(self, full_defn: dict):
        history = [d for arr in full_defn["history"].values() for d in arr]
        self.definition = max(history, key=lambda x: int(x["versions"]["first"]))

    def _set_dates(self, first_added_value: dict):
        vals = [datetime.fromisoformat(v) for v in first_added_value.values()]

        self.first_added = min(vals)
        self.last_change = max(vals)

    def get_first_added(self) -> datetime:
        return self.first_added

    def get_last_change(self) -> datetime:
        return self.last_change

    def get_schema(self, addtlProps: Any) -> Any:
        # Get the schema based on the probe type
        if self.get_type() == "scalar":
            ptype = self.get("details", "kind")
            if ptype == "boolean":
                pschema = {"type": "boolean"}
            elif ptype == "string":
                pschema = {"type": "string"}
            elif ptype == "uint":
                pschema = {"type": "integer"}
            else:
                raise Exception("Unknown scalar type " + ptype)
        elif self.get_type() == "histogram":
            pschema = self.histogram_schema

        # Add nested level if keyed
        if self.get("details", "keyed"):
            final_schema = {"type": "object", "additionalProperties": pschema}
        else:
            final_schema = pschema

        return final_schema


class GleanProbe(Probe):

    all_pings_keyword = "all_pings"
    first_added_key = "first_added"

    def __init__(self, identifier: str, definition: dict, *, pings: List[str] = None):
        self._set_dates(definition)
        self._set_definition(definition)
        super().__init__(identifier, definition)

        if pings is not None:
            self._update_all_pings(pings)

    def _update_all_pings(self, pings: List[str]):
        if GleanProbe.all_pings_keyword in self.definition["send_in_pings"]:
            self.definition["send_in_pings"] = pings

    def _set_definition(self, full_defn: dict):
        self.definition = max(full_defn[self.history_key],
                              key=lambda x: datetime.fromisoformat(x["dates"]["last"]))

    def _set_dates(self, definition: dict):
        vals = [
            datetime.fromisoformat(d["dates"]["first"])
            for d in definition[self.history_key]
        ]

        self.first_added = min(vals)
        self.last_change = max(vals)

    def get_first_added(self) -> datetime:
        return self.first_added

    def get_last_change(self) -> datetime:
        return self.last_change

    def get_schema(self, addtlProps: Any) -> Any:
        if addtlProps is None:
            raise SchemaException("Additional Properties cannot be missing for Glean probes")
        return addtlProps
