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

    config = Config(config_data)
    schemas = schema_generator.generate_schema(config, split=split)
    dump_schema(schemas, out_dir, pretty)


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
def generate_glean_ping(config, out_dir, split, pretty, repo):
    if split:
        raise NotImplementedError("Splitting of Glean pings is not yet supported.")

    if out_dir:
        out_dir = Path(out_dir)

    if repo is not None:
        repos = [repo]
    else:
        repos = GleanPing.get_repos()

    with open(config, 'r') as f:
        config_data = yaml.load(f)

    config = Config(config_data)

    for repo_name, repo_id in repos:
        write_schema(repo_name, repo_id, config, out_dir, split, pretty)


def write_schema(repo, repo_id, config, out_dir, split, pretty):
    schema_generator = GleanPing(repo)
    schemas = schema_generator.generate_schema(config, split=False)
    dump_schema(schemas, out_dir.joinpath(repo_id), pretty)


def dump_schema(schemas, out_dir, pretty):
    json_dump_args = {'cls': SchemaEncoder}
    if pretty:
        json_dump_args['indent'] = 4
        json_dump_args['separators'] = (',', ':')

    if not out_dir:
        print(json.dumps(schemas, **json_dump_args))

    else:
        for name, _schemas in schemas.items():
            ping_out_dir = out_dir.joinpath(name)
            if not ping_out_dir.exists():
                ping_out_dir.mkdir(parents=True)
            for i, schema in enumerate(_schemas):
                fname = ping_out_dir.joinpath("{}.{}.schema.json".format(name, i+1))
                with open(fname, 'w') as f:
                    f.write(json.dumps(schema, **json_dump_args))


@click.group()
def main(args=None):
    """Command line utility for mozilla-schema-generator."""
    pass


main.add_command(generate_main_ping)
main.add_command(generate_glean_ping)


if __name__ == "__main__":
    sys.exit(main())
