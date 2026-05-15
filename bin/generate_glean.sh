#!/bin/bash

# Generate glean pings for all apps and write to schema_out/ at the repo root
# The steps here mirror the job to create the generated-schemas branch

set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")/.."

mozilla-schema-generator generate-glean-pings --out-dir schema_out/ --pretty

for schema in $(find schema_out -name "*.schema.json" -type f); do
    bin/metadata_merge metadata/ "$schema"
done

# Add transpiled BQ schemas
find schema_out -type f -name "*.schema.json" | while read -r fname; do
    bq_out=${fname/schema.json/bq}
    mkdir -p "$(dirname "$bq_out")"
    jsonschema-transpiler \
        --resolve drop \
        --type bigquery \
        --normalize-case \
        --force-nullable \
        --tuple-struct \
            "$fname" > "$bq_out"
done

mozilla-schema-generator generate-glean-pings  --pretty  --generic-schema --out-dir schema_out