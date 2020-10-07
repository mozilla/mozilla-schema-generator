import shutil
from pathlib import Path

import gitdb
import pytest
from click.testing import CliRunner
from git import Git, Repo
from mozilla_schema_generator.validate_bigquery import (
    check_evolution,
    checkout_copy_schemas_revisions,
    compute_compact_columns,
    copy_schemas,
    local_validation,
)


@pytest.fixture()
def tmp_git(tmp_path):
    src = Path(__file__).parent / "resources" / "mozilla-pipeline-schemas"
    src_repo = Repo(src)
    src_repo.git.checkout("master")
    src_repo.git.checkout("generated-schemas")
    Git(tmp_path).clone(src)
    path = tmp_path / "mozilla-pipeline-schemas"
    repo = Repo(path)
    repo.git.checkout("master")
    repo.git.checkout("generated-schemas")
    return path


def test_tmp_git(tmp_git):
    repo = Repo(tmp_git)
    assert not repo.bare
    assert repo.head.ref.name == "generated-schemas"
    repo.git.checkout("master")
    assert repo.head.ref.name == "master"


def test_compute_compact_columns():
    schema = [
        {"name": "leaf", "mode": "NULLABLE", "type": "INT64"},
        {"name": "repeated", "mode": "REPEATED", "type": "INT64"},
        {
            "name": "nested",
            "mode": "NULLABLE",
            "type": "RECORD",
            "fields": [{"name": "leaf", "type": "INT64", "mode": "NULLABLE"}],
        },
        {
            "name": "repeated_nested",
            "mode": "REPEATED",
            "type": "RECORD",
            "fields": [{"name": "leaf", "type": "INT64", "mode": "NULLABLE"}],
        },
    ]
    expected = sorted(
        [
            "root.leaf INT64",
            "root.nested.leaf INT64",
            "root.repeated.[] INT64",
            "root.repeated_nested.[].leaf INT64",
        ]
    )
    output = compute_compact_columns(schema)
    assert output == expected


def test_check_evolution():
    assert check_evolution(["a", "b"], ["a", "b"]) == 0
    assert check_evolution(["a"], ["a", "b"]) == 0
    assert check_evolution(["a", "b"], ["a"]) == 1


def test_copy_schemas(tmp_path, tmp_git):
    dst = copy_schemas("HEAD", tmp_git, tmp_path)
    bq = list(dst.glob("*.bq"))
    txt = list(dst.glob("*.txt"))
    assert len(bq) > 0, "no bq schemas detected"
    assert len(bq) == len(txt)
    repo = Repo(tmp_git)
    # the dst name encodes the revision, we should always be able to use the
    # first 6 characters to find commit in the repository.
    assert repo.rev_parse(dst.name[:6]) == repo.head.commit


def test_checkout_copy_schema_revisions(tmp_path, tmp_git):
    repo = Repo(tmp_git)
    head_ref = "generated-schemas"
    base_ref = "generated-schemas~10"
    head, base = checkout_copy_schemas_revisions(head_ref, base_ref, tmp_git, tmp_path)
    assert head and base
    assert repo.rev_parse(head.name[:8]) == repo.rev_parse(head_ref)
    assert repo.rev_parse(base.name[:8]) == repo.rev_parse(base_ref)


def test_checkout_copy_schema_revisions_fails_dirty(tmp_path, tmp_git):
    repo = Repo(tmp_git)
    head_ref = "generated-schemas"
    base_ref = "generated-schemas~10"
    (tmp_git / "schemas/telemetry/main/main.4.schema.json").write_text("dirty")
    with pytest.raises(ValueError):
        head, base = checkout_copy_schemas_revisions(
            head_ref, base_ref, tmp_git, tmp_path
        )


def test_checkout_copy_schema_revisions_fails_and_reverts_state(tmp_path, tmp_git):
    repo = Repo(tmp_git)
    with pytest.raises(gitdb.exc.BadName):
        head, base = checkout_copy_schemas_revisions(
            "generated-schemas", "branch-name-that-doesnt-exist", tmp_git, tmp_path
        )
    assert repo.head.ref.name == "generated-schemas"
    with pytest.raises(ValueError):
        # no schemas found, since master branch does not have generated schemas
        # it's okay to have leftover files in the artifact directory
        head, base = checkout_copy_schemas_revisions(
            "generated-schemas", "master", tmp_git, tmp_path
        )
    assert repo.head.ref.name == "generated-schemas"


def test_local_validation_command(tmp_path, tmp_git):
    # use a known revision, in case the submodule ever gets changed
    # this uses generated-schemas and generated-schemas~1
    head = "a6011d9"
    base = "485be1e"
    res = CliRunner().invoke(
        local_validation,
        [
            "--head",
            head,
            "--base",
            base,
            "--repository",
            tmp_git.as_posix(),
            "--artifact",
            tmp_path.as_posix(),
        ],
    )
    assert res.exit_code == 0
    assert "no incompatible changes detected" in res.output
    # in the reverse direction, we are removing a column
    res = CliRunner().invoke(
        local_validation,
        [
            "--head",
            base,
            "--base",
            head,
            "--repository",
            tmp_git.as_posix(),
            "--artifact",
            tmp_path.as_posix(),
        ],
    )
    assert res.exit_code == 1
    assert "found incompatible changes" in res.output
