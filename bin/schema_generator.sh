#!/bin/bash

# TODO: Update schema mapping for validation
# TODO: Handle overwriting glean schemas

GCS_BUCKET="mozilla-generated-schemas"
MPS_BRANCH="generated-schemas"

# 0. Install dependencies

cargo install --git https://github.com/acmiyaguchi/jsonschema-transpiler --branch 0.2 --force

virtualenv mgs-venv 
source mgs-venv/bin/activate
pip install -U mozilla-schema-generator

# 1. Pull in all schemas from MPS

SCHEMAS_DIR="schemas"
BASE_DIR="/Users/frankbertsch/repos/sandbox"

cp metadata_merge.py $BASE_DIR
cd $BASE_DIR
rm -rf mozilla-pipeline-schemas

git clone https://www.github.com/mozilla-services/mozilla-pipeline-schemas
cd mozilla-pipeline-schemas/$SCHEMAS_DIR
git checkout ping-metadata

# 2. Remove all non-json schemas (e.g. parquet)

find . -not -name "*.schema.json" -type f | xargs rm

# 3. Generate new schemas

mozilla-schema-generator generate-glean-ping --out-dir . --pretty
mozilla-schema-generator generate-main-ping --out-dir . --pretty --split

# 4. Add metadata to all json schemas, drop metadata schemas

metadata_dir="metadata"
telemetry_metadata="$metadata_dir/telemetry-ingestion/telemetry-ingestion.1.schema.json"
structured_metadata="$metadata_dir/structured-ingestion/structured-ingestion.1.schema.json"

find ./telemetry -type f -exec metadata_merge $telemetry_metadata {} ";"
find . -path ./telemetry -prune -o -type f -exec metadata_merge $structured_metadata {} ";"

rm -rf $metadata_dir

# 5. Add transpiled avro and BQ schemas

find . -type f|while read fname; do
    AVRO_OUT=${fname/schema.json/avro}
    BQ_OUT=${fname/schema.json/bq}
    jsonschema-transpiler --type avro $fname > $AVRO_OUT
    jsonschema-transpiler --type bigquery $fname> $BQ_OUT
done

# 6. Upload to GCS

gsutil -m cp -r $SCHEMA_DIR gs://$GCS_BUCKET/

# 7. Push to branch of MPS
# Note: This method will keep a changelog of releases.
# If we delete and newly checkout branches everytime,
# that will contain a changelog of changes.

cd ../

rm -rf templates tests validation
find . -not -name "*.schema.json" -type f | xargs git add
git checkout $MPS_BRANCH || git checkout -b $MPS_BRANCH
git commit -a -m "Auto-push from schema generation"

git push --repo https://name:password@bitbucket.org/name/repo.git
