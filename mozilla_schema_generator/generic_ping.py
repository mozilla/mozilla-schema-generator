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
            c.name: self.make_schemas(env, probes, c, split, max_size)
            for c in configs
        }

        if split:
            schemas[self.extra_schema_key] = self.make_extra_schema(schema, probes, configs)

        return schemas

    @staticmethod
    def make_schemas(env: Schema, probes: List[Probe], config: Config,
                     split: bool, max_size: int) -> List[Schema]:
        """
        Fill in probes based on the config, and keep only the env
        parts of the schema. Throw away everything else.
        """
        schema_elements = sorted(config.get_schema_elements(probes), key=lambda x: x[1])
        schemas = []

        # TODO: Should env be checked to be a subset of schema?
        final_schema = env.clone()
        for schema_key, probe in schema_elements:
            try:
                addtlProps = env.get(schema_key + ("additionalProperties",))
            except KeyError:
                addtlProps = None

            probe_schema = Schema(probe.get_schema(addtlProps))

            if split and final_schema.get_size() + probe_schema.get_size() > max_size:
                schemas.append(final_schema)
                final_schema = env.clone()

            final_schema.set_schema_elem(
                schema_key + ("properties", probe.name),
                probe_schema.schema)
            final_schema.set_schema_elem(
                schema_key + ("additionalProperties",),
                False)
            final_schema.delete_group_from_schema(schema_key + ("propertyNames",))

        return schemas + [final_schema]

    @staticmethod
    def make_extra_schema(schema: Schema, probes: List[Probe],
                          configs: List[Config]) -> List[Schema]:
        """
        Given the list of probes and the configuration,
        return the schema that has everything but those sections that we
        filled in already.

        TODO: Split the extra schema, when needed (e.g. extra.0.schema.json, extra.1.schema.json)
        """
        schema = schema.clone()

        # Get the schema elements we already filled in for the other tables
        schema_elements = [
            schema_key
            for _config in configs
            for schema_key, _ in _config.get_schema_elements(probes)
        ]

        # Delete those from the schema
        for schema_key in schema_elements:
            schema.delete_group_from_schema(schema_key)

        return [schema]

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
