#!/usr/bin/env python3
import click
from pathlib import Path
from git import Repo
from shutil import copyfile
import json
import difflib
import sys


BASE_DIR = Path("/app").resolve()


@click.group()
def validate():
    """Click command group."""
    pass


def compute_compact_columns(document):
    def traverse(prefix, columns):
        res = []
        for node in columns:
            name = node["name"] + (".[]" if node["mode"] == "REPEATED" else "")
            dtype = node["type"]
            if dtype == "RECORD":
                res += traverse(f"{prefix}.{name}", node["fields"])
            else:
                res += [f"{prefix}.{name} {dtype}"]
        return res

    res = traverse("root", document)
    return sorted(res)


@validate.command()
@click.option("--head", default="HEAD")
@click.option(
    "--repository",
    type=click.Path(exists=True, file_okay=False),
    default=BASE_DIR / "mozilla-pipeline-schemas",
)
@click.option(
    "--artifact",
    type=click.Path(file_okay=False),
    default=BASE_DIR / "validate_schema_evolution",
)
def copy(head, repository, artifact):
    """Copy BigQuery schemas to a directory as an intermediary step for schema
    evolution checks."""
    src = Path(repository)
    repo = Repo(repository)
    dst = Path(artifact) / repo.rev_parse(head).name_rev.replace(" ", "_")
    dst.mkdir(parents=True, exist_ok=True)
    schemas = sorted(src.glob("**/*.bq"))
    if not schemas:
        raise click.ClickException("no schemas found")
    for path in schemas:
        namespace = path.parts[-3]
        doc = path.parts[-1]
        qualified = f"{namespace}.{doc}"
        click.echo(qualified)
        copyfile(path, dst / qualified)

        # also generate something easy to diff
        cols = compute_compact_columns(json.loads(path.read_text()))
        compact_filename = ".".join(qualified.split(".")[:-1]) + ".txt"
        (dst / compact_filename).write_text("\n".join(cols))


def check_evolution(base, head, verbose=False):
    def nop(*args, **kwargs):
        pass

    log = print if verbose else nop

    a, b = set(base), set(head)
    is_error = 0
    # error condition
    base_only = a - b
    if len(base_only) > 0:
        log("items removed from the base")
        log("\n".join([f"-{x}" for x in base_only]))
        log("")
        # set the status
        is_error = 1

    # informative only
    head_only = b - a
    if len(head_only) > 0:
        log("items added to the base")
        log("\n".join([f"+{x}" for x in head_only]))
        log("")
    return is_error


@validate.command()
@click.option("--head", type=str, default="local-working-branch")
@click.option("--base", type=str, default="generated-schemas")
@click.option(
    "--repository",
    type=click.Path(exists=True, file_okay=False),
    default=BASE_DIR / "mozilla-pipeline-schemas",
)
@click.option(
    "--artifact",
    type=click.Path(file_okay=False),
    default=BASE_DIR / "validate_schema_evolution",
)
def local(head, base, repository, artifact):
    """Validate schemas using a heuristic from the compact schemas."""
    repo = Repo(repository)

    # NOTE: we are using the revision + branch name. If the local-working-branch
    # is overwritten, it is possible that the specific name-rev no longer
    # exists.
    head_rev = repo.rev_parse(head).name_rev.replace(" ", "_")
    base_rev = repo.rev_parse(base).name_rev.replace(" ", "_")
    artifact_path = Path(artifact)

    assert (artifact_path / head_rev).exists()
    assert (artifact_path / base_rev).exists()

    is_error = 0

    # look at the compact schemas
    head_files = (artifact_path / head_rev).glob("*.txt")
    base_files = (artifact_path / base_rev).glob("*.txt")

    a = set([p.name for p in base_files])
    b = set([p.name for p in head_files])

    is_error |= check_evolution(a, b, verbose=True)

    for schema_name in a & b:
        base = artifact_path / base_rev / schema_name
        head = artifact_path / head_rev / schema_name
        base_data = base.read_text().split("\n")
        head_data = head.read_text().split("\n")
        diff = "\n".join(
            # control lines contain a newline at the end
            [
                line.strip()
                for line in difflib.unified_diff(
                    base_data,
                    head_data,
                    fromfile=base.as_posix(),
                    tofile=head.as_posix(),
                    n=1,
                )
            ]
        )
        if not diff:
            # no difference detected
            continue
        # check if this is an error condition
        print(diff + "\n")
        is_error |= check_evolution(base_data, head_data)

    if not is_error:
        click.echo("no incompatible changes detected")
    else:
        click.echo("found incompatible changes")

    sys.exit(is_error)


if __name__ == "__main__":
    validate()
