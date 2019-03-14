
import click
import sys
import yaml
import json
from pathlib import Path

from .main_ping import MainPing
from .config import Config
from .schema import SchemaEncoder


@click.command()
@click.argument(
    'config',
    type=click.Path(
        dir_okay=False,
        file_okay=True,
        writable=False,
        exists=True,
    ),
    default="configs/main.yaml",
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

    with open(config, 'r') as f:
        config_data = yaml.load(f)

    config = Config(config_data)
    schemas = schema_generator.generate_schema(config, split=split)

    json_dump_args = {'cls': SchemaEncoder}
    if pretty:
        json_dump_args['indent'] = 4
        json_dump_args['separators'] = (',', ':')

    if not out_dir:
        print(json.dumps(schemas, **json_dump_args))

    else:
        out_dir = Path(out_dir)
        if not out_dir.exists():
            out_dir.mkdir()
        for name, _schemas in schemas.items():
            for i, schema in enumerate(_schemas):
                fname = out_dir.joinpath("main.{}.{}.schema.json".format(name, i))
                with open(fname, 'w') as f:
                    f.write(json.dumps(schema, **json_dump_args))


@click.group()
def main(args=None):
    """Command line utility for mozilla-schema-generator."""
    pass


main.add_command(generate_main_ping)


if __name__ == "__main__":
    sys.exit(main())
