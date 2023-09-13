import json
import re
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Dict, Tuple

# most metadata fields are added to the bq schema directly and left out of the json schema, but
# fields here appear in the json schema and must be explicitly included in all resulting pings
ADDITIONAL_METADATA_FIELDS = [
    "client_id",
    "clientId",
    "client_info",
]


def _get_path(out_dir, namespace, doctype, version):
    return out_dir / namespace / doctype / f"{doctype}.{version}.schema.json"


def _path_string(*path):
    return ".".join(path)


def _schema_copy(src, pattern, dst=None, delete=True, prefix=()):
    if src.get("type") != "object" or "properties" not in src:
        # only recurse into objects with explicitly defined properties
        return None
    src_props = src["properties"]
    dst_props = {}
    for name, src_subschema in list(src_props.items()):
        path = ".".join((*prefix, name))
        if pattern.fullmatch(path):
            prop = src_props.pop(name) if delete else deepcopy(src_props[name])
        else:
            prop = _schema_copy(
                src_subschema,
                pattern,
                dst=None if dst is None else dst["properties"].get(name, None),
                delete=delete,
                prefix=(*prefix, name),
            )
        if prop is not None:
            dst_props[name] = prop
    if dst_props:
        if dst is None:
            return {"properties": dst_props, "type": "object"}
        else:
            dst["properties"].update(dst_props)
            return dst
    return None


def _copy_metadata(source, destination):
    for key in ("$id", "$schema", "mozPipelineMetadata"):
        if key not in source:
            continue
        elif isinstance(source[key], dict):
            destination[key] = deepcopy(source[key])
        else:
            destination[key] = source[key]
    for key in ADDITIONAL_METADATA_FIELDS:
        if key in source["properties"]:
            destination["properties"][key] = deepcopy(source["properties"][key])


def _update_pipeline_metadata(schema, namespace, doctype, version):
    pipeline_metadata = schema["mozPipelineMetadata"]
    pipeline_metadata["bq_dataset_family"] = namespace
    pipeline_metadata["bq_table"] = f'{doctype.replace("-", "_")}_v{version}'


def _target_as_tuple(target: Dict[str, str]) -> Tuple[str, str, str]:
    return (
        target["document_namespace"],
        target["document_type"],
        target["document_version"],
    )


def generate(config_data, out_dir: Path) -> Dict[str, Dict[str, Dict[str, Dict]]]:
    """Read in pings from disk and split fields into new subset pings.

    If configured, also produce a remainder ping with all the fields that weren't moved.
    """
    schemas = defaultdict(lambda: defaultdict(dict))
    # read in pings and split them according to config
    for source in config_data:
        src_namespace, src_doctype, src_version = _target_as_tuple(source)
        src_path = _get_path(out_dir, src_namespace, src_doctype, src_version)
        schema = json.loads(src_path.read_text())

        config = schema["mozPipelineMetadata"].pop("split_config")
        for subset_config in config["subsets"]:
            dst_namespace, dst_doctype, dst_version = _target_as_tuple(subset_config)
            pattern = re.compile(subset_config["pattern"])
            subset = _schema_copy(schema, pattern, delete=True)
            assert subset is not None, "Subset pattern matched no paths"
            if "extra_pattern" in subset_config:
                # match paths where the schema must be present in the remainder because
                # schemas cannot delete fields, but data must only go to the subset.
                pattern = re.compile(subset_config["extra_pattern"])
                subset = _schema_copy(schema, pattern, dst=subset, delete=False)
                assert subset is not None, "Subset extra_pattern matched no paths"
            _copy_metadata(schema, subset)
            _update_pipeline_metadata(subset, dst_namespace, dst_doctype, dst_version)
            schemas[dst_namespace][dst_doctype][dst_version] = subset
        remainder_config = config.get("remainder")
        if remainder_config:
            dst_namespace, dst_doctype, dst_version = _target_as_tuple(remainder_config)
            # no need to copy metadata
            _update_pipeline_metadata(schema, dst_namespace, dst_doctype, dst_version)
            schemas[dst_namespace][dst_doctype][dst_version] = schema
    return schemas
