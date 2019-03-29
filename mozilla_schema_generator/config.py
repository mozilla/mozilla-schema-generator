# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

from .utils import _get, prepend_properties
import queue
from collections import defaultdict
# TODO: s/probes/probe
from .probes import Probe
from .matcher import Matcher

from typing import Dict, List, Tuple


class Config(object):

    match_key = "match"
    default_schema_name = "full"

    def __init__(self, *args, **kwargs):
        if "matchers" in kwargs:
            self.name = args[0]
            self.matchers = kwargs["matchers"]
        else:
            self.name = self.default_schema_name
            self._set_matchers(args[0])

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

    def _get_splits(self) -> Dict[str, Dict[Tuple[str], Matcher]]:
        """
        Find the splits that we need to make. Each
        self.table_group_key is it's own split.
        """
        splits = defaultdict(dict)
        for key, matcher in self.matchers.items():
            splits[matcher.get_table_group()][key] = matcher

        return splits

    def split(self) -> List[Config]:
        """
        Split this config into multiple configs.
        """
        splits = self._get_splits()
        return [
            Config(name, matchers=matchers)
            for name, matchers in splits.items()
        ]

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
