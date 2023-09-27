# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

import queue
from typing import Dict, List, Tuple

from .matcher import Matcher

# TODO: s/probes/probe
from .probes import Probe
from .utils import _get, prepend_properties


class Config(object):
    match_key = "match"

    def __init__(self, *args, **kwargs):
        self.name = args[0]
        if "matchers" in kwargs:
            self.matchers = kwargs["matchers"]
        else:
            self._set_matchers(args[1])

    def _set_matchers(self, config: dict) -> Dict[Tuple[str], Matcher]:
        """
        Transform the nested config into a single dictionary
        """
        keys = queue.SimpleQueue()
        matchers = {}

        for key, v in config.items():
            if isinstance(v, dict):
                keys.put((key,))

        while not keys.empty():
            key = keys.get()
            elem = _get(config, key)

            if self.match_key in elem:
                matchers[key] = Matcher(elem[self.match_key])
            else:
                for k, v in elem.items():
                    if isinstance(v, dict):
                        keys.put(key + (k,))

        self.matchers = matchers

    def get_match_keys(self) -> List[Tuple[str]]:
        return [prepend_properties(key) for key in self.matchers.keys()]

    def get_schema_elements(self, probes: List[Probe]) -> List[Tuple[tuple, Probe]]:
        """
        Given a schema and set of probes, get a list of probe and
        the location in the schema where those probes should be
        inputted.
        """
        schema_elements = []

        for key, matcher in self.matchers.items():
            # Get the element we are filling in from the schema
            schema_key = prepend_properties(key)

            # Get the probes for the fill-in
            schema_elements += [(schema_key, p) for p in probes if matcher.matches(p)]

        return schema_elements
