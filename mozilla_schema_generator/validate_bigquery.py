#!/usr/bin/env python3
import difflib
import json
import sys
from pathlib import Path
from shutil import copyfile
from typing import Tuple

import click
from git import Repo

BASE_DIR = Path("/app").resolve()


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


def copy_schemas(head: str, repository: Path, artifact: Path) -> Path:
    """Copy BigQuery schemas to a directory as an intermediary step for schema
    evolution checks."""
    src = Path(repository)
    repo = Repo(repository)
    dst = Path(artifact) / repo.rev_parse(head).name_rev.replace(" ", "_")
    dst.mkdir(parents=True, exist_ok=True)
    schemas = sorted(src.glob("**/*.bq"))
    if not schemas:
        raise ValueError("no schemas found")
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
    return dst


def checkout_copy_schemas_revisions(
    head: str, base: str, repository: Path, artifact: Path
) -> Tuple[Path, Path]:
    """Checkout two revisions of the schema repository into the artifact
    directory. This returns paths to the head and the base directories."""
    repo = Repo(repository)
    if repo.is_dirty():
        raise ValueError("the repo is dirty, stash any changes and try again")
    head_path = None
    base_path = None
    # get the head to the closest symbolic reference
    current_ref = repo.git.rev_parse("HEAD", abbrev_ref=True)
    # note: if we try using --abbrev-ref on something like
    # `generated-schemas~1`, we may end up with an empty string. We should
    # fallback to the commit-hash if used.
    head_rev = repo.rev_parse(head).hexsha
    base_rev = repo.rev_parse(base).hexsha
    try:
        repo.git.checkout(head_rev)
        head_path = copy_schemas(head_rev, repository, artifact)
        repo.git.checkout(base_rev)
        base_path = copy_schemas(base_rev, repository, artifact)
    finally:
        repo.git.checkout(current_ref)
    return head_path, base_path


def parse_incompatibility_allowlist(allowlist: Path) -> list:
    res = []
    if not allowlist or not allowlist.exists():
        return res
    lines = [line.strip() for line in allowlist.read_text().split("\n")]
    for line in lines:
        if not line or line.startswith("#"):
            continue
        res.append(line)
    return res


@click.group()
def validate():
    """Click command group."""


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
@click.option(
    "--incompatibility-allowlist",
    type=click.Path(dir_okay=False),
    help="newline delimited globs of schemas with allowed schema incompatibilities",
    default=BASE_DIR / "mozilla-schema-generator/incompatibility-allowlist",
)
def local_validation(head, base, repository, artifact, incompatibility_allowlist):
    """Validate schemas using a heuristic from the compact schemas."""
    head_path, base_path = checkout_copy_schemas_revisions(
        head, base, repository, artifact
    )
    is_error = 0

    # look at the compact schemas
    head_files = (head_path).glob("*.txt")
    base_files = (base_path).glob("*.txt")

    # also look at the exceptions
    allowed_incompatibility_base_files = []
    if incompatibility_allowlist:
        for glob in parse_incompatibility_allowlist(Path(incompatibility_allowlist)):
            allowed_incompatibility_base_files += list((base_path).glob(f"{glob}.txt"))

    a = set([p.name for p in base_files])
    b = set([p.name for p in head_files])
    allowed_incompatibility = set([p.name for p in allowed_incompatibility_base_files])

    # Check that we're not removing any schemas. If there are exceptions, we
    # remove this from the base set before checking for evolution.
    if allowed_incompatibility:
        print("allowing incompatible changes in the following documents:")
        print("\n".join([f"\t{x}" for x in allowed_incompatibility]))
    is_error |= check_evolution((a - allowed_incompatibility), b, verbose=True)

    for schema_name in a & b:
        base = base_path / schema_name
        head = head_path / schema_name
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
        err_code = check_evolution(base_data, head_data)
        if err_code and schema_name in allowed_incompatibility:
            print("found incompatible changes, but continuing")
            continue
        is_error |= err_code

    if not is_error:
        click.echo("no incompatible changes detected")
    else:
        click.echo("found incompatible changes")

    sys.exit(is_error)


if __name__ == "__main__":
    validate()
