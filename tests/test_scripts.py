# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Tests for `mozilla-schema-generator` scripts.
"""

import json
import pathlib
import shutil
import subprocess

import pytest


class TestSchemaAliasing(object):
    base_dir = "./test-schemas"
    test_aliases_path = "test-aliases.json"
    source_namespace = "namespace"
    source_doctype = "doctype"
    source_version = "1"

    @pytest.fixture(autouse=True)
    def setup_teardown_dir(self):
        dir_path = pathlib.Path(self.base_dir)
        path = dir_path / self.source_namespace / self.source_doctype
        json_file = path / f"{self.source_doctype}.{self.source_version}.schema.json"
        bq_file = path / f"{self.source_doctype}.{self.source_version}.bq"

        json_file.parent.mkdir(parents=True)
        json_file.write_text("{}")
        bq_file.touch()

        yield

        shutil.rmtree(dir_path)
        pathlib.Path(self.test_aliases_path).unlink()

    def write_aliases(self, aliases):
        path = pathlib.Path(self.test_aliases_path)
        with open(path, "w") as f:
            json.dump(aliases, f)

        return path

    def test_aliasing_same_namespace(self):
        test_doctype = "test-doctype"
        aliases_path = self.write_aliases(
            {
                self.source_namespace: {
                    test_doctype: {
                        "1": {
                            "source-namespace": self.source_namespace,
                            "source-doctype": self.source_doctype,
                            "source-version": self.source_version,
                        }
                    }
                }
            }
        )

        res = subprocess.run(("./bin/alias_schemas", str(aliases_path), self.base_dir))

        assert res.returncode == 0

        test_path = pathlib.Path(self.base_dir) / self.source_namespace / test_doctype
        assert (test_path / f"{test_doctype}.1.schema.json").exists()

    def test_aliasing_new_namespace(self):
        test_namespace = "test-namespace"
        test_doctype = "test-doctype"
        test_version = "1"
        aliases_path = self.write_aliases(
            {
                test_namespace: {
                    test_doctype: {
                        test_version: {
                            "source-namespace": self.source_namespace,
                            "source-doctype": self.source_doctype,
                            "source-version": self.source_version,
                        }
                    }
                }
            }
        )

        res = subprocess.run(("./bin/alias_schemas", str(aliases_path), self.base_dir))

        assert res.returncode == 0

        test_path = pathlib.Path(self.base_dir) / test_namespace / test_doctype
        assert (test_path / f"{test_doctype}.1.schema.json").exists()

    def test_no_aliasing(self):
        aliases_path = self.write_aliases({})
        res = subprocess.run(("./bin/alias_schemas", str(aliases_path), self.base_dir))

        assert res.returncode == 0

        # should only have bq and json schema for source
        test_path = pathlib.Path(self.base_dir)
        assert len(list(test_path.iterdir())) == 1
        assert len(list((test_path / self.source_namespace).iterdir())) == 1
        assert (
            len(
                list(
                    (test_path / self.source_namespace / self.source_doctype).iterdir()
                )
            )
            == 2
        )

    def test_missing_source_errors(self):
        test_namespace = "test-namespace"
        test_doctype = "test-doctype"
        aliases_path = self.write_aliases(
            {
                test_namespace: {
                    test_doctype: {
                        "source-namespace": "missing-namespace",
                        "source-doctype": self.source_doctype,
                    }
                }
            }
        )

        res = subprocess.run(("./bin/alias_schemas", str(aliases_path), self.base_dir))

        assert res.returncode != 0

    def test_improper_name_errors(self):
        test_namespace = "@test-namespace"
        test_doctype = "test-doctype"
        aliases_path = self.write_aliases(
            {
                test_namespace: {
                    test_doctype: {
                        "source-namespace": "missing-namespace",
                        "source-doctype": self.source_doctype,
                    }
                }
            }
        )

        res = subprocess.run(("./bin/alias_schemas", str(aliases_path), self.base_dir))
        assert res.returncode != 0
