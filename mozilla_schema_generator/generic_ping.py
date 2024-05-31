# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import logging
import os
import pathlib
import re
from json.decoder import JSONDecodeError
from typing import Dict, List

import requests

from .config import Config
from .probes import Probe
from .schema import Schema, SchemaException

logger = logging.getLogger(__name__)


class GenericPing(object):
    probe_info_base_url = "https://probeinfo.telemetry.mozilla.org"
    default_encoding = "utf-8"
    default_max_size = 12900  # https://bugzilla.mozilla.org/show_bug.cgi?id=1688633
    cache_dir = pathlib.Path(os.environ.get("MSG_PROBE_CACHE_DIR", ".probe_cache"))

    def __init__(self, schema_url, env_url, probes_url, mps_branch="main"):
        self.branch_name = mps_branch
        self.schema_url = schema_url.format(branch=self.branch_name)
        self.env_url = env_url.format(branch=self.branch_name)
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
        self, config: Config, *, max_size: int = None
    ) -> Dict[str, Schema]:
        schema = self.get_schema()
        env = self.get_env()

        probes = self.get_probes()

        if max_size is None:
            max_size = self.default_max_size

        if env.get_size() >= max_size:
            raise SchemaException(
                "Environment must be smaller than max_size {}".format(max_size)
            )

        if schema.get_size() >= max_size:
            raise SchemaException(
                "Schema must be smaller than max_size {}".format(max_size)
            )

        schemas = {config.name: self.make_schema(schema, probes, config, max_size)}

        if any(schema.get_size() > max_size for schema in schemas.values()):
            raise SchemaException(
                "Schema must be smaller or equal max_size {}".format(max_size)
            )

        return schemas

    @staticmethod
    def make_schema(
        env: Schema, probes: List[Probe], config: Config, max_size: int
    ) -> Schema:
        """
        Fill in probes based on the config, and keep only the env
        parts of the schema. Throw away everything else.
        """
        schema_elements = sorted(config.get_schema_elements(probes), key=lambda x: x[1])

        schema = env.clone()
        for schema_key, probe in schema_elements:
            try:
                addtlProps = env.get(schema_key + ("additionalProperties",))
            except KeyError:
                addtlProps = None

            probe_schema = Schema(probe.get_schema(addtlProps)).clone()

            schema.set_schema_elem(
                schema_key + ("properties", probe.name), probe_schema.schema
            )

        # Remove all additionalProperties (#22)
        for key in config.get_match_keys():
            try:
                schema.delete_group_from_schema(
                    key + ("propertyNames",), propagate=False
                )
            except KeyError:
                pass

            try:
                schema.delete_group_from_schema(
                    key + ("additionalProperties",), propagate=True
                )
            except KeyError:
                pass

        return schema

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

        cache_file = GenericPing.cache_dir / GenericPing._slugify(url)
        # protect against multiple writers to the cache:
        # https://github.com/mozilla/mozilla-schema-generator/pull/210
        try:
            with open(cache_file, "x") as f:
                f.write(val)
        except FileExistsError:
            pass

    @staticmethod
    def _retrieve_from_cache(url: str) -> str:
        return (GenericPing.cache_dir / GenericPing._slugify(url)).read_text()

    @staticmethod
    def _get_json_str(url: str) -> str:
        if GenericPing._present_in_cache(url):
            return GenericPing._retrieve_from_cache(url)

        headers = {}
        if url.startswith(GenericPing.probe_info_base_url):
            # For probe-info-service requests, set the cache-control header to force
            # google cloud cdn to bypass the cache
            headers["Cache-Control"] = "no-cache"

        r = requests.get(url, headers=headers, stream=True)
        r.raise_for_status()

        json_bytes = b""

        try:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    json_bytes += chunk
        except ValueError as e:
            raise ValueError("Could not parse " + url) from e

        final_json = json_bytes.decode(r.encoding or GenericPing.default_encoding)
        GenericPing._add_to_cache(url, final_json)

        return final_json

    @staticmethod
    def _get_json(url: str) -> dict:
        try:
            return json.loads(GenericPing._get_json_str(url))
        except JSONDecodeError:
            logging.error("Unable to process JSON for url: %s", url)
            raise
