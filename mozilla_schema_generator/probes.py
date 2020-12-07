# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


from __future__ import annotations

import json
from datetime import datetime
from typing import Any, List

from .schema import SchemaException
from .utils import _get


class Probe(object):

    type_key = "type"
    name_key = "name"
    history_key = "history"

    def __init__(self, identifier: str, definition: dict):
        self.id = identifier
        self.type = definition[self.type_key]
        self.name = definition[self.name_key]

    def __repr__(self):
        return json.dumps(
            {
                "id": self.id,
                "type": self.type,
                "name": self.name,
                "description": self.description,
            }
        )

    def get_type(self) -> str:
        return self.type

    def get_name(self) -> str:
        return self.name

    def get_description(self) -> str:
        return self.description

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

    histogram_schema = {"type": "string"}

    parent_processes = {"main"}

    child_processes = {"content", "gpu", "extension", "dynamic", "socket"}

    processes_map = {
        "all_childs": child_processes,
        "all_children": child_processes,
        "all": child_processes | parent_processes,
    }

    def __init__(self, identifier: str, definition: dict):
        self._set_dates(definition[self.first_added_key])
        self._set_definition(definition)
        self._set_description(self.definition)
        super().__init__(identifier, definition)

    def _set_definition(self, full_defn: dict):
        history = [d for arr in full_defn[self.history_key].values() for d in arr]
        self.definition = max(history, key=lambda x: int(x["versions"]["first"]))
        self.definition["name"] = full_defn[self.name_key]
        self._set_processes(history)

    def _set_processes(self, history):
        # Include all historical processes
        processes = {
            p for d in history for p in d["details"].get("record_in_processes", [])
        }
        processes = {
            sub_p for p in processes for sub_p in self.processes_map.get(p, [p])
        }
        self.definition["details"]["record_in_processes"] = processes

    def _set_dates(self, first_added_value: dict):
        vals = [datetime.fromisoformat(v) for v in first_added_value.values()]

        self.first_added = min(vals)
        self.last_change = max(vals)

    def _set_description(self, definition):
        self.description = None
        if "description" in definition:
            self.description = definition["description"]
            # BigQuery limits descriptions to a maximum of 1024 characters,
            # so we truncate anything longer than 1000.
            if len(self.description) >= 1000:
                self.description = self.description[:1000] + "…"

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

        if self.description is not None:
            pschema["description"] = self.description

        # Add nested level if keyed
        if self.get("details", "keyed"):
            final_schema = {"type": "object", "additionalProperties": pschema}
        else:
            final_schema = pschema

        return final_schema


class GleanProbe(Probe):

    all_pings_keywords = ("all-pings", "all_pings")
    first_added_key = "first_added"

    def __init__(self, identifier: str, definition: dict, *, pings: List[str] = None):
        self._set_dates(definition)
        self._set_definition(definition)
        self._set_description(self.definition)
        super().__init__(identifier, definition)

        defn_pings = set(
            [
                p
                for d in definition[self.history_key]
                for p in d.get("send_in_pings", ["metrics"])
            ]
        )
        self.definition["send_in_pings"] = defn_pings

        if pings is not None:
            self._update_all_pings(pings)

    def _update_all_pings(self, pings: List[str]):
        if any(
            [
                kw in self.definition["send_in_pings"]
                for kw in GleanProbe.all_pings_keywords
            ]
        ):
            self.definition["send_in_pings"] = set(pings)

    def _set_definition(self, full_defn: dict):
        # Expose the entire history, for special casing of the probe.
        self.definition_history = list(
            sorted(
                full_defn[self.history_key],
                key=lambda x: datetime.fromisoformat(x["dates"]["last"]),
                reverse=True,
            )
        )

        # The canonical definition for up-to-date schemas
        self.definition = self.definition_history[0]
        self.definition["name"] = full_defn[self.name_key]

    def _set_dates(self, definition: dict):
        vals = [
            datetime.fromisoformat(d["dates"]["first"])
            for d in definition[self.history_key]
        ]

        self.first_added = min(vals)
        self.last_change = max(vals)

    def _set_description(self, definition):
        if "description" in definition:
            self.description = definition["description"]
        else:
            self.description = None

    def get_first_added(self) -> datetime:
        return self.first_added

    def get_last_change(self) -> datetime:
        return self.last_change

    def get_schema(self, addtlProps: Any) -> Any:
        if addtlProps is None:
            raise SchemaException(
                "Additional Properties cannot be missing for Glean probes"
            )

        if self.description:
            addtlProps["description"] = self.description

        return addtlProps
