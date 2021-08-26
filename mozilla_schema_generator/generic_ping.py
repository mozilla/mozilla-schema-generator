# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import json
import os
import pathlib
import re
from typing import Dict, List

import requests

from .config import Config
from .probes import Probe
from .schema import Schema, SchemaException


class GenericPing(object):

    probe_info_base_url = "https://probeinfo.telemetry.mozilla.org"
    default_encoding = "utf-8"
    default_max_size = 11000  # https://bugzilla.mozilla.org/show_bug.cgi?id=1688633
    extra_schema_key = "extra"
    cache_dir = pathlib.Path(os.environ.get("MSG_PROBE_CACHE_DIR", ".probe_cache"))

    def __init__(self, schema_url, env_url, probes_url, mps_branch="main"):
        self.schema_url = schema_url.format(branch=mps_branch)
        self.env_url = env_url.format(branch=mps_branch)
        self.probes_url = probes_url

    def get_schema(self) -> Schema:
        return Schema(self._get_json(self.schema_url))

    def get_env(self) -> Schema:
        return Schema(self._get_json(self.env_url))

    def get_probes(self) -> List[Probe]:
        return [
            Probe(_id, defn) for _id, defn in self._get_json(self.probes_url).items()
        ]

    def generate_schema(
        self, config: Config, *, split: bool = None, max_size: int = None
    ) -> Dict[str, List[Schema]]:
        schema = self.get_schema()
        env = self.get_env()

        probes = self.get_probes()

        if split is None:
            split = False
        if max_size is None:
            max_size = self.default_max_size

        if env.get_size() >= max_size:
            raise SchemaException(
                "Environment must be smaller than max_size {}".format(max_size)
            )

        # TODO: Allow splits of extra schema, if necessary
        if schema.get_size() >= max_size:
            raise SchemaException(
                "Schema must be smaller than max_size {}".format(max_size)
            )

        if split:
            configs = config.split()
        else:
            configs = [config]
            env = schema

        schemas = {
            c.name: self.make_schemas(env, probes, c, split, max_size) for c in configs
        }

        if split:
            schemas[self.extra_schema_key] = self.make_extra_schema(
                schema, probes, configs
            )

        if any(
            schema.get_size() > max_size for _, s in schemas.items() for schema in s
        ):
            raise SchemaException(
                "Schema must be smaller or equal max_size {}".format(max_size)
            )

        return schemas

    @staticmethod
    def make_schemas(
        env: Schema, probes: List[Probe], config: Config, split: bool, max_size: int
    ) -> List[Schema]:
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

            probe_schema = Schema(probe.get_schema(addtlProps)).clone()

            if split and final_schema.get_size() + probe_schema.get_size() > max_size:
                schemas.append(final_schema)
                final_schema = env.clone()

            final_schema.set_schema_elem(
                schema_key + ("properties", probe.name), probe_schema.schema
            )

        # Remove all additionalProperties (#22)
        schemas.append(final_schema)
        for s in schemas:
            for key in config.get_match_keys():
                try:
                    s.delete_group_from_schema(
                        key + ("propertyNames",), propagate=False
                    )
                except KeyError:
                    pass

                try:
                    s.delete_group_from_schema(
                        key + ("additionalProperties",), propagate=True
                    )
                except KeyError:
                    pass

        return schemas

    @staticmethod
    def make_extra_schema(
        schema: Schema, probes: List[Probe], configs: List[Config]
    ) -> List[Schema]:
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
    def _slugify(text: str) -> str:
        """Get a valid slug from an arbitrary string"""
        value = re.sub(r"[^\w\s-]", "", text.lower()).strip()
        return re.sub(r"[-\s]+", "-", value)

    @staticmethod
    def _present_in_cache(url: str) -> bool:
        return (GenericPing.cache_dir / GenericPing._slugify(url)).exists()

    @staticmethod
    def _add_to_cache(url: str, val: str):
        GenericPing.cache_dir.mkdir(parents=True, exist_ok=True)

        (GenericPing.cache_dir / GenericPing._slugify(url)).write_text(val)

    @staticmethod
    def _retrieve_from_cache(url: str) -> str:
        return (GenericPing.cache_dir / GenericPing._slugify(url)).read_text()

    @staticmethod
    def _get_json_str(url: str) -> str:
        no_param_url = re.sub(r"\?.*", "", url)

        if GenericPing._present_in_cache(no_param_url):
            return GenericPing._retrieve_from_cache(no_param_url)

        r = requests.get(url, stream=True)
        r.raise_for_status()

        json_bytes = b""

        try:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    json_bytes += chunk
        except ValueError as e:
            raise ValueError("Could not parse " + url) from e

        final_json = json_bytes.decode(r.encoding or GenericPing.default_encoding)
        GenericPing._add_to_cache(no_param_url, final_json)

        return final_json

    @staticmethod
    def _get_json(url: str) -> dict:
        if url.startswith(GenericPing.probe_info_base_url):
            # For probe-info-service requests, add
            # random query param to force cloudfront
            # to bypass the cache
            url += f"?t={datetime.datetime.utcnow().isoformat()}"
        return json.loads(GenericPing._get_json_str(url))
