#!/usr/bin/env python

import json
import requests
import re
from copy import deepcopy

"""
This script creates N schemas, each representing one Bigquery table for the main ping. Every table contains:
  - environment
  - application
  - clientId
  - creationDate
  - id
  - type
  - version

The tables are split up as follows. If a single table below exceeds 10k columns, then it will be further split, with each table containing a subset
 of the available fields and all of the fields listed above.

1. Non-probe data
- info
- addonHistograms
- lateWrites
- ver
- log
- fileIOReports
- addonDetails
- childPayloads
- UIMeasurements
- threadHangStats
- simpleMeasurements
- chromeHangs
- slowSQL
- webrtc
- slowSQLStartup
- gc

2. Histograms

3. Keyed Histograms

4. Scalars

5. Keyed Scalars

"""

base_schema_url = "https://raw.githubusercontent.com/mozilla-services/mozilla-pipeline-schemas/dev/schemas/telemetry/main/main.4.schema.json"
base_probes_url = "https://probeinfo.telemetry.mozilla.org/firefox/all/main/all_probes"
base_fx_versions_url = "https://product-details.mozilla.org/1.0/firefox_versions.json"


# Prefer nightly definitions over beta and release
channels = ["nightly", "beta", "release"]

# The channel name in fx_versions_url JSON file
channels_versions_names = ["FIREFOX_NIGHTLY", "LATEST_FIREFOX_RELEASED_DEVEL_VERSION", "LATEST_FIREFOX_VERSION"]

TELEMETRY_TO_JSCHEMA_TYPE_MAP = {
  "uint": "integer",
  "boolean": "boolean",
  "string": "string",
}

# TODO: memoize
def get_json(url):
  local_filename = url.split('/')[-1]
  r = requests.get(url, stream=True)

  with open(local_filename, 'wb') as f:
    for chunk in r.iter_content(chunk_size=1024): 
      if chunk:
        f.write(chunk)

  with open(local_filename, 'r') as f:
    return json.load(f)


def get_base_schema():
  return get_json(base_schema_url)


def get_probes():
  return get_json(base_probes_url)


def get_fx_versions():
  return get_json(base_fx_versions_url)


def trim_version(full_version):
  match = re.match(r"([0-9]+).[0-9a-zA-Z]+", full_version)
  if not match:
    return None
  else:
    return int(match.group(1))


def get_current_versions():
  version_data = get_fx_versions()

  return {
    name: trim_version(version_data[label])
    for name, label in zip(channels, channels_versions_names)
  }

# TODO: memoize instead
versions = get_current_versions()


# This function assumes that the json file is well-formed
# and returns the first definition found that is current
def standard_definition(d):
  history = d.get("history")

  for channel in channels:
    if channel in history:
      # only deal with the most recent ones
      definition = history.get(channel)[0]
      if (definition["expiry_version"] == "never" or
         int(definition["expiry_version"]) > versions[channel]):
        definition["name"] = d["name"]
        return definition 

  return None


def get_scalar_schema(definition):
  jschema_type = TELEMETRY_TO_JSCHEMA_TYPE_MAP[definition["details"]["kind"]]
  schema = { "type": jschema_type }
  if definition["details"]["keyed"]:
    return {
      "type": "object",
      "additionalProperties": schema
    }
  else:
    return schema


def get_histogram_schema(base_schema, definition):
  schema = deepcopy(base_schema)

  if definition["details"]["keyed"]:
    return {
      "type": "object",
      "additionalProperties": schema
    }
  else:
    return schema


def generate_histogram_schema(probes, process, keyed, histogram_schema):
  definitions = [standard_definition(d) for name, d in probes.iteritems() if name.startswith("histogram")]
  histograms = [definition for definition in definitions
                if definition is not None
                and keyed == definition["details"]["keyed"]
                and process in definition["details"].get("record_in_processes", ["main", "content"])]

  return {
    definition["name"]: get_histogram_schema(histogram_schema, definition)
    for definition in histograms
  }


def generate_scalar_schema(probes, process, keyed):
  all_scalars = [p for name, p in probes.iteritems() if name.startswith("scalar")]
  definitions = [standard_definition(d) for d in all_scalars]
  scalars = [definition for definition in definitions
             if definition is not None
             and keyed == definition["details"]["keyed"]
             and process in definition["details"].get("record_in_processes", ["main", "content"])]

  return {
    definition["name"]: get_scalar_schema(definition)
    for definition in scalars 
  }


def generate_schema():
  probes = get_probes()
  base_schema = get_base_schema()
  histogram_schema = base_schema["properties"]["payload"]["properties"]["histograms"]["additionalProperties"]

  main_histograms = generate_histogram_schema(probes, "main", False, histogram_schema)
  main_keyed_histograms = generate_histogram_schema(probes, "main", True, histogram_schema)

  base_schema["properties"]["payload"]["properties"]["histograms"]["properties"] = main_histograms
  base_schema["properties"]["payload"]["properties"]["keyedHistograms"]["properties"] = main_keyed_histograms 

  #del base_schema["properties"]["payload"]["properties"]["histograms"]
  #del base_schema["properties"]["payload"]["properties"]["keyedHistograms"]

  # big ol' sigh
  process_map = {"parent": "main"}

  for process in base_schema["properties"]["payload"]["properties"]["processes"]["properties"]:
    process_probe_name = process_map.get(process, process)

    histograms = generate_histogram_schema(probes, process_probe_name, False, histogram_schema)
    keyed_histograms = generate_histogram_schema(probes, process_probe_name, True, histogram_schema)
    scalars = generate_scalar_schema(probes, process_probe_name, False)
    keyed_scalars = generate_scalar_schema(probes, process_probe_name, True)

    base_schema["properties"]["payload"]["properties"]["processes"]["properties"][process]["properties"]["histograms"]["properties"] = histograms
    base_schema["properties"]["payload"]["properties"]["processes"]["properties"][process]["properties"]["keyedHistograms"]["properties"] = keyed_histograms
    base_schema["properties"]["payload"]["properties"]["processes"]["properties"][process]["properties"]["scalars"]["properties"] = scalars
    base_schema["properties"]["payload"]["properties"]["processes"]["properties"][process]["properties"]["keyedScalars"]["properties"] = keyed_scalars

    #del base_schema["properties"]["payload"]["properties"]["processes"]["properties"][process]["properties"]["histograms"]
    #del base_schema["properties"]["payload"]["properties"]["processes"]["properties"][process]["properties"]["keyedHistograms"]

    # we don't need these
    del base_schema["properties"]["payload"]["properties"]["processes"]["properties"][process]["properties"]["scalars"]["additionalProperties"]
    del base_schema["properties"]["payload"]["properties"]["processes"]["properties"][process]["properties"]["keyedScalars"]["additionalProperties"]


  return base_schema


def main():
  schema = generate_schema()
  print json.dumps(schema, sort_keys=True, indent=4, separators=(',', ': '))

if __name__ == "__main__":
  main()
