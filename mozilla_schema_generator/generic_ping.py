# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import requests

from .schema import Schema, SchemaException
from .probes import Probe
from .config import Config
from typing import Dict, List


class GenericPing(object):

    default_encoding = 'utf-8'
    default_max_size = 9000  # 10k col limit in BQ
    extra_schema_key = "extra"

    def __init__(self, schema_url, env_url, probes_url):
        self.schema_url = schema_url
        self.env_url = env_url
        self.probes_url = probes_url

    def get_schema(self) -> Schema:
        return Schema(self._get_json(self.schema_url))

    def get_env(self) -> Schema:
        return Schema(self._get_json(self.env_url))

    def get_probes(self) -> List[Probe]:
        return [Probe(_id, defn) for _id, defn in self._get_json(self.probes_url).items()]

    def generate_schema(self, config: Config, *, split: bool = None, max_size: int = None) \
            -> Dict[str, List[Schema]]:
        schema = self.get_schema()
        env = self.get_env()
        probes = self.get_probes()

        if split is None:
            split = False
        if max_size is None:
            max_size = self.default_max_size

        if env.get_size() >= max_size:
            raise SchemaException("Environment must be smaller than max_size {}".format(max_size))

        # TODO: Allow splits of extra schema, if necessary
        if schema.get_size() >= max_size:
            raise SchemaException("Schema must be smaller than max_size {}".format(max_size))

        if split:
            configs = config.split()
        else:
            configs = [config]
            env = schema

        schemas = {
            c.name: schema.make_schemas(env, probes, c, split, max_size)
            for c in configs
        }

        if split:
            schema.make_extra_schema(probes, configs)
            schemas[self.extra_schema_key] = [schema]

        return schemas

    @staticmethod
    def _get_json_str(url: str) -> dict:
        r = requests.get(url, stream=True)
        final_json = ""

        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                final_json += chunk.decode(r.encoding or GenericPing.default_encoding)

        return final_json

    @staticmethod
    def _get_json(url: str) -> dict:
        return json.loads(GenericPing._get_json_str(url))
