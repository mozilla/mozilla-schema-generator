# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import click
import sys
import yaml
import json
import re
from pathlib import Path

from .common_ping import CommonPing
from .main_ping import MainPing
from .glean_ping import GleanPing
from .config import Config
from .schema import Schema, SchemaEncoder

ROOT_DIR = Path(__file__).parent
CONFIGS_DIR = ROOT_DIR / "configs"
SCHEMA_NAME_RE = re.compile(r".+/([a-zA-Z0-9_-]+)\.([0-9]+)\.schema\.json")


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
@click.option(
    '--mps-branch',
    help=("If specified, the source branch of "
          "mozilla-pipeline-schemas to reference"),
    required=False,
)
def generate_main_ping(config, out_dir, split, pretty, mps_branch):
    schema_generator = MainPing(mps_branch=mps_branch)
    if out_dir:
        out_dir = Path(out_dir)

    with open(config, 'r') as f:
        config_data = yaml.safe_load(f)

    config = Config("main", config_data)
    schemas = schema_generator.generate_schema(config, split=split)
    dump_schema(schemas, out_dir, pretty, version=4)


@click.command()
@click.argument(
    'config-dir',
    type=click.Path(
        dir_okay=True,
        file_okay=False,
        writable=False,
        exists=True,
    ),
    default=CONFIGS_DIR,
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
    '--common-pings-config',
    default="common_pings.json",
    help=("File containing URLs to schemas and configs "
          "of pings in the common ping format."),
)
@click.option(
    '--mps-branch',
    help=("If specified, the source branch of "
          "mozilla-pipeline-schemas to reference"),
    required=False,
)
def generate_common_pings(config_dir, out_dir, split, pretty, common_pings_config, mps_branch):
    if split:
        raise NotImplementedError("Splitting of common pings is not yet supported.")

    if out_dir:
        out_dir = Path(out_dir)

    common_pings = []

    with open(common_pings_config, 'r') as f:
        common_pings = json.load(f)

    for common_ping in common_pings:
        schema_generator = CommonPing(common_ping["schema_url"], mps_branch=mps_branch)

        config_data = {}

        if "config" in common_ping:
            with open(config_dir / common_ping["config"], 'r') as f:
                config_data = yaml.safe_load(f)

        m = re.match(SCHEMA_NAME_RE, common_ping["schema_url"])
        name = m.group(1)
        version = m.group(2)
        config = Config(name, config_data)

        schemas = schema_generator.generate_schema(config, split=False)

        dump_schema(schemas, out_dir, pretty, version=int(version))


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
@click.option(
    '--mps-branch',
    help=("If specified, the source branch of "
          "mozilla-pipeline-schemas to reference"),
    required=False,
)
def generate_glean_pings(config, out_dir, split, pretty, repo, generic_schema, mps_branch):
    if split:
        raise NotImplementedError("Splitting of Glean pings is not yet supported.")

    if out_dir:
        out_dir = Path(out_dir)

    repos = GleanPing.get_repos()

    if repo is not None:
        repos = [(r_name, r_id) for r_name, r_id in repos if r_id == repo]

    with open(config, 'r') as f:
        config_data = yaml.safe_load(f)

    config = Config("glean", config_data)

    for repo_name, repo_id in repos:
        write_schema(repo_name, repo_id, config, out_dir, split, pretty, generic_schema, mps_branch)


def write_schema(repo, repo_id, config, out_dir, split, pretty, generic_schema, mps_branch):
    schema_generator = GleanPing(repo, repo_id, mps_branch=mps_branch)
    schemas = schema_generator.generate_schema(config, split=False, generic_schema=generic_schema)
    dump_schema(schemas, out_dir and out_dir.joinpath(repo_id), pretty)


def dump_schema(schemas, out_dir, pretty, *, version=1):
    json_dump_args = {
        'cls': SchemaEncoder
    }
    if pretty:
        json_dump_args.update({
            'indent': 4,
            'separators': (',', ':'),
            'sort_keys': True,
        })

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


@click.command()
@click.argument(
    'orig',
    type=click.Path(
        dir_okay=True,
        file_okay=False,
        exists=True,
    ),
)
@click.argument(
    'altered',
    type=click.Path(
        dir_okay=True,
        file_okay=False,
        exists=True,
    ),
)
@click.option(
    '-v',
    '--verbose',
    count=True
)
def check_schema_changes(orig, altered, verbose):
    from_files = {str(p)[len(str(orig))+1:] for p in Path(orig).rglob('*.schema.json')}
    to_files = {str(p)[len(str(altered))+1:] for p in Path(altered).rglob('*.schema.json')}

    removed_files = from_files - to_files
    added_files = to_files - from_files

    def read_json(f):
        with open(f) as json_file:
            return json.load(json_file)

    all_schema_changes = {fname: "File Removed (disallowed)" for fname in removed_files}

    for fname in set(to_files) - added_files:
        if verbose > 1:
            click.echo("Comparing " + fname)
        from_json = read_json(f'{orig}/{fname}')
        to_json = read_json(f'{altered}/{fname}')

        schema_changes = Schema.get_invalid_schema_changes(from_json, to_json, verbosity=verbose)
        if schema_changes:
            all_schema_changes[fname] = '\n'.join([f'{col}: {change}' for col, change in schema_changes.items()])

    file_invalid_changes = '\n\n'.join(
        [
            f'{fname}\n{changes}' 
            for fname, changes in all_schema_changes.items()
        ]
    )

    if all_schema_changes:
        if verbose > 0:
            click.echo("\nSchema Incompatible Changes Found\n")
            click.echo(file_invalid_changes)
        sys.exit(1)


@click.group()
def main(args=None):
    """Command line utility for mozilla-schema-generator."""
    import logging
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)


main.add_command(generate_main_ping)
main.add_command(generate_glean_pings)
main.add_command(generate_common_pings)
main.add_command(check_schema_changes)


if __name__ == "__main__":
    sys.exit(main())
