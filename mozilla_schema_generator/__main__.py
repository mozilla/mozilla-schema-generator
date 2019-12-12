# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import click
import sys
import yaml
import json
from pathlib import Path

from .main_ping import MainPing
from .glean_ping import GleanPing
from .config import Config
from .schema import SchemaEncoder

ROOT_DIR = Path(__file__).parent
CONFIGS_DIR = ROOT_DIR / "configs"


@click.command()
@click.argument(
    'config',
    type=click.Path(
        dir_okay=False,
        file_okay=True,
        writable=False,
        exists=True,
    ),
    default=CONFIGS_DIR / "main.yaml",
)
@click.option(
    '--out-dir',
    help=("The directory to write the schema files to. "
          "If not provided, writes the schemas to stdout."),
    type=click.Path(
        dir_okay=True,
        file_okay=False,
        writable=True,
    ),
    required=False
)
@click.option(
    '--split',
    is_flag=True,
    help=("If provided, splits the schema into "
          "smaller sub-schemas"),
)
@click.option(
    '--pretty',
    is_flag=True,
    help=("If specified, pretty-prints the JSON "
          "schemas that are outputted. Otherwise "
          "the schemas will be on one line."),
)
def generate_main_ping(config, out_dir, split, pretty):
    schema_generator = MainPing()
    if out_dir:
        out_dir = Path(out_dir)

    with open(config, 'r') as f:
        config_data = yaml.load(f)

    config = Config("main", config_data)
    schemas = schema_generator.generate_schema(config, split=split)
    dump_schema(schemas, out_dir, pretty, version=4)


@click.command()
@click.argument(
    'config',
    type=click.Path(
        dir_okay=False,
        file_okay=True,
        writable=False,
        exists=True,
    ),
    default=CONFIGS_DIR / "glean.yaml",
)
@click.option(
    '--out-dir',
    help=("The directory to write the schema files to. "
          "If not provided, writes the schemas to stdout."),
    type=click.Path(
        dir_okay=True,
        file_okay=False,
        writable=True,
    ),
    required=False
)
@click.option(
    '--split',
    is_flag=True,
    help=("If provided, splits the schema into "
          "smaller sub-schemas"),
)
@click.option(
    '--pretty',
    is_flag=True,
    help=("If specified, pretty-prints the JSON "
          "schemas that are outputted. Otherwise "
          "the schemas will be on one line."),
)
@click.option(
    '--repo',
    help=("The repository id to write the schemas of. "
          "If not specified, writes the schemas of all "
          "repositories."),
    required=False,
    type=str
)
@click.option(
    '--generic-schema',
    is_flag=True,
    help=("When specified, schemas are not filled in, "
          "but instead the generic schema is used for "
          "every application's glean pings.")
)
def generate_glean_pings(config, out_dir, split, pretty, repo, generic_schema):
    if split:
        raise NotImplementedError("Splitting of Glean pings is not yet supported.")

    if out_dir:
        out_dir = Path(out_dir)

    repos = GleanPing.get_repos()

    if repo is not None:
        repos = [(r_name, r_id) for r_name, r_id in repos if r_id == repo]

    with open(config, 'r') as f:
        config_data = yaml.load(f)

    config = Config("glean", config_data)

    for repo_name, repo_id in repos:
        write_schema(repo_name, repo_id, config, out_dir, split, pretty, generic_schema)


def write_schema(repo, repo_id, config, out_dir, split, pretty, generic_schema):
    schema_generator = GleanPing(repo)
    schemas = schema_generator.generate_schema(config, split=False, generic_schema=generic_schema)
    dump_schema(schemas, out_dir.joinpath(repo_id), pretty)


def dump_schema(schemas, out_dir, pretty, *, version=1):
    json_dump_args = {'cls': SchemaEncoder}
    if pretty:
        json_dump_args['indent'] = 4
        json_dump_args['separators'] = (',', ':')

    if not out_dir:
        print(json.dumps(schemas, **json_dump_args))

    else:
        for name, _schemas in schemas.items():
            # Bug 1601270; we transform ping names from snake_case to kebab-case;
            # we can remove this line once all snake_case probes have converted.
            name = name.replace('_', '-')
            ping_out_dir = out_dir.joinpath(name)
            if not ping_out_dir.exists():
                ping_out_dir.mkdir(parents=True)

            if len(_schemas) > 1:
                raise Exception("Table splitting is currently unsupported")

            schema = _schemas[0]
            fname = ping_out_dir.joinpath("{}.{}.schema.json".format(name, version))
            with open(fname, 'w') as f:
                f.write(json.dumps(schema, **json_dump_args))


@click.group()
def main(args=None):
    """Command line utility for mozilla-schema-generator."""
    import logging
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)


main.add_command(generate_main_ping)
main.add_command(generate_glean_pings)


if __name__ == "__main__":
    sys.exit(main())
