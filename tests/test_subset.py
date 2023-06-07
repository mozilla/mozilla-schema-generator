import json
from pathlib import Path
from textwrap import dedent

import yaml

from mozilla_schema_generator import subset_pings


def test_subset(tmp_path: Path):
    config_path = tmp_path / "subset.yaml"
    config_path.write_text(
        dedent(
            """
            - document_namespace: test
              document_type: preserve
              document_version: '1'
            """
        )
    )
    config_data = yaml.safe_load(config_path.read_text())

    preserve_schema = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "mozPipelineMetadata": {
            "bq_dataset_family": "test",
            "bq_metadata_format": "structured",
            "bq_table": "preserve_v1",
            "split_config": {
                "preserve_original": True,
                "subsets": [
                    {
                        "document_namespace": "test",
                        "document_type": "subset",
                        "document_version": "1",
                        "pattern": ".*int",
                    },
                ],
                "remainder": {
                    "document_namespace": "test",
                    "document_type": "remainder",
                    "document_version": "1",
                },
            },
        },
        "properties": {
            "client_id": {"type": "string"},
            "payload": {
                "type": "object",
                "properties": {
                    "int": {"type": "integer"},
                    "string": {"type": "string"},
                },
                "required": [],
            },
            "test_int": {"type": "integer"},
            "test_string": {"type": "string"},
        },
        "required": [],
    }

    expect_remainder_schema = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "mozPipelineMetadata": {
            "bq_dataset_family": "test",
            "bq_metadata_format": "structured",
            "bq_table": "remainder_v1",
        },
        "properties": {
            "client_id": {"type": "string"},
            "payload": {
                "type": "object",
                "properties": {"string": {"type": "string"}},
                "required": [],
            },
            "test_string": {"type": "string"},
        },
        "required": [],
    }

    expect_subset_schema = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "mozPipelineMetadata": {
            "bq_dataset_family": "test",
            "bq_metadata_format": "structured",
            "bq_table": "subset_v1",
        },
        "properties": {
            "client_id": {"type": "string"},
            "payload": {
                "type": "object",
                "properties": {"int": {"type": "integer"}},
            },
            "test_int": {"type": "integer"},
        },
    }

    preserve_path = tmp_path / "test" / "preserve" / "preserve.1.schema.json"
    preserve_path.parent.mkdir(parents=True)
    preserve_path.write_text(json.dumps(preserve_schema, indent=2))

    schemas = subset_pings.generate(config_data=config_data, out_dir=tmp_path)
    # convert json representation for evaluation
    schemas = json.loads(json.dumps(schemas))

    assert schemas == {
        "test": {
            "remainder": {"1": [expect_remainder_schema]},
            "subset": {"1": [expect_subset_schema]},
        }
    }
