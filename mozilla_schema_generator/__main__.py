# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import re
import sys
from pathlib import Path

import click
import yaml

from .bhr_ping import BhrPing
from .common_ping import CommonPing
from .config import Config
from .glean_ping import GleanPing
from .main_ping import MainPing
from .schema import SchemaEncoder

ROOT_DIR = Path(__file__).parent
CONFIGS_DIR = ROOT_DIR / "configs"
SCHEMA_NAME_RE = re.compile(r".+/([a-zA-Z0-9_-]+)\.([0-9]+)\.schema\.json")


def _apply_options(func, options):
    """Apply options to a command."""
    for option in options:
        func = option(func)
    return func


def common_options(func):
    """Common options for schema generator commands."""
    return _apply_options(
        func,
        [
            click.option(
                "--out-dir",
                help=(
                    "The directory to write the schema files to. "
                    "If not provided, writes the schemas to stdout."
                ),
                type=click.Path(dir_okay=True, file_okay=False, writable=True),
                required=False,
            ),
            click.option(
                "--split",
                is_flag=True,
                help=("If provided, splits the schema into " "smaller sub-schemas"),
            ),
            click.option(
                "--pretty",
                is_flag=True,
                help=(
                    "If specified, pretty-prints the JSON "
                    "schemas that are outputted. Otherwise "
                    "the schemas will be on one line."
                ),
            ),
            click.option(
                "--mps-branch",
                help=(
                    "If specified, the source branch of "
                    "mozilla-pipeline-schemas to reference"
                ),
                required=False,
                type=str,
                default="main",
            ),
        ],
    )


@click.command()
@click.argument(
    "config",
    type=click.Path(dir_okay=False, file_okay=True, writable=False, exists=True),
    default=CONFIGS_DIR / "main.yaml",
)
@common_options
def generate_main_ping(config, out_dir, split, pretty, mps_branch):
    schema_generator = MainPing(mps_branch=mps_branch)
    if out_dir:
        out_dir = Path(out_dir)

    with open(config, "r") as f:
        config_data = yaml.safe_load(f)

    config = Config("main", config_data)
    schemas = schema_generator.generate_schema(config, split=False)
    # schemas introduces an extra layer to the actual schema
    dump_schema(schemas, out_dir, pretty, version=4)


@click.command()
@common_options
def generate_bhr_ping(out_dir, split, pretty, mps_branch):
    schema_generator = BhrPing(mps_branch=mps_branch)
    if out_dir:
        out_dir = Path(out_dir)

    config = Config("bhr", {})
    schemas = schema_generator.generate_schema(config, split=split)
    dump_schema(schemas, out_dir, pretty, version=4)


@click.command()
@click.argument(
    "config-dir",
    type=click.Path(dir_okay=True, file_okay=False, writable=False, exists=True),
    default=CONFIGS_DIR,
)
@common_options
@click.option(
    "--common-pings-config",
    default="common_pings.json",
    help=(
        "File containing URLs to schemas and configs "
        "of pings in the common ping format."
    ),
)
def generate_common_pings(
    config_dir, out_dir, split, pretty, mps_branch, common_pings_config
):
    if split:
        raise NotImplementedError("Splitting of common pings is not yet supported.")

    if out_dir:
        out_dir = Path(out_dir)

    common_pings = []

    with open(common_pings_config, "r") as f:
        common_pings = json.load(f)

    for common_ping in common_pings:
        schema_generator = CommonPing(common_ping["schema_url"], mps_branch=mps_branch)

        config_data = {}

        if "config" in common_ping:
            with open(config_dir / common_ping["config"], "r") as f:
                config_data = yaml.safe_load(f)

        m = re.match(SCHEMA_NAME_RE, common_ping["schema_url"])
        name = m.group(1)
        version = m.group(2)
        config = Config(name, config_data)

        schemas = schema_generator.generate_schema(config, split=False)

        dump_schema(schemas, out_dir, pretty, version=int(version))


@click.command()
@click.argument(
    "config",
    type=click.Path(dir_okay=False, file_okay=True, writable=False, exists=True),
    default=CONFIGS_DIR / "glean.yaml",
)
@common_options
@click.option(
    "--repo",
    help=(
        "The repository id to write the schemas of. "
        "If not specified, writes the schemas of all "
        "repositories."
    ),
    required=False,
    type=str,
)
@click.option(
    "--generic-schema",
    is_flag=True,
    help=(
        "When specified, schemas are not filled in, "
        "but instead the generic schema is used for "
        "every application's glean pings."
    ),
)
def generate_glean_pings(
    config, out_dir, split, pretty, mps_branch, repo, generic_schema
):
    if split:
        raise NotImplementedError("Splitting of Glean pings is not yet supported.")

    if out_dir:
        out_dir = Path(out_dir)

    repos = GleanPing.get_repos()

    if repo is not None:
        repos = [r for r in repos if r["app_id"] == repo]

    with open(config, "r") as f:
        config_data = yaml.safe_load(f)

    config = Config("glean", config_data)

    for repo in repos:
        write_schema(repo, config, out_dir, split, pretty, generic_schema, mps_branch)


def write_schema(repo, config, out_dir, split, pretty, generic_schema, mps_branch):
    schema_generator = GleanPing(repo, mps_branch=mps_branch)
    schemas = schema_generator.generate_schema(
        config, split=False, generic_schema=generic_schema
    )
    dump_schema(schemas, out_dir and out_dir.joinpath(repo["app_id"]), pretty)


def dump_schema(schemas, out_dir, pretty, *, version=1):
    json_dump_args = {"cls": SchemaEncoder}
    if pretty:
        json_dump_args.update(
            {"indent": 4, "separators": (",", ":"), "sort_keys": True}
        )

    if not out_dir:
        print(json.dumps(schemas, **json_dump_args))

    else:
        for name, _schemas in schemas.items():
            # Bug 1601270; we transform ping names from snake_case to kebab-case;
            # we can remove this line once all snake_case probes have converted.
            name = name.replace("_", "-")
            ping_out_dir = out_dir.joinpath(name)
            if not ping_out_dir.exists():
                ping_out_dir.mkdir(parents=True)

            if len(_schemas) > 1:
                raise Exception("Table splitting is currently unsupported")

            schema = _schemas[0]
            fname = ping_out_dir.joinpath("{}.{}.schema.json".format(name, version))
            with open(fname, "w") as f:
                f.write(json.dumps(schema, **json_dump_args))


@click.group()
def main(args=None):
    """Command line utility for mozilla-schema-generator."""
    import logging

    logging.basicConfig(stream=sys.stderr, level=logging.INFO)


main.add_command(generate_main_ping)
main.add_command(generate_bhr_ping)
main.add_command(generate_glean_pings)
main.add_command(generate_common_pings)


if __name__ == "__main__":
    sys.exit(main())
