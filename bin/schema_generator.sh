#!/bin/bash

# TODO: Update schema mapping for validation
# TODO: Handle overwriting glean schemas
# TODO: Include Main Ping from schema generation
# TODO: What the heck to do with pioneer-study, a non-nested namespace

if [[ -z $MOZILLA_PIPELINE_SCHEMAS_SECRET_GIT_SSHKEY ]]; then
    echo "Missing secret key" 1>&2
    exit 1
fi

mkdir -p /app/.ssh
echo $MOZILLA_PIPELINE_SCHEMAS_SECRET_GIT_SSHKEY > /app/.ssh/id_rsa

chmod 700 "$HOME/.ssh"
chmod 700 "$HOME/.ssh/id_rsa"

DEV_BRANCH="ping-metadata" # Branch we'll work on
MPS_BRANCH="generated-schemas" # Branch we'll push to

# 0. Install dependencies

cargo install jsonschema-transpiler

virtualenv mgs-venv 
source mgs-venv/bin/activate
pip install -U mozilla-schema-generator

# 1. Pull in all schemas from MPS

SCHEMAS_DIR="schemas"
BASE_DIR="/app"

cd $BASE_DIR
rm -rf mozilla-pipeline-schemas

git clone https://www.github.com/mozilla-services/mozilla-pipeline-schemas.git
cd mozilla-pipeline-schemas/$SCHEMAS_DIR
git checkout $DEV_BRANCH

# 2. Remove all non-json schemas (e.g. parquet)

find . -not -name "*.schema.json" -type f | xargs rm

# 3. Generate new schemas

mozilla-schema-generator generate-glean-ping --out-dir . --pretty
mozilla-schema-generator generate-main-ping --out-dir ./telemetry --pretty --split

# 3a. Keep only whitelisted schemas

# Pioneer-study is not nested, remove it
rm -rf pioneer-study

# Replace newlines with backticks (hard to do with sed): cat | tr
# Remove the last backtick; it's the file-ending newline: rev | cut | rev
# Replace backticks with "\|" (can't do that with tr): sed
# Find directories that don't match any of the regex expressions: find
# Remove them: rm
cat /app/bin/whitelist | tr '\n' '`' | rev | cut -c 2- | rev | sed -e 's/`/\\\\|/g' | xargs -I % find . -type d -regextype sed -not -regex '.*/\(%\|metadata/.*\)' -mindepth 2 | xargs rm -rf

# Some namespace are now empty, remove them
find . -type d -empty -delete

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

# 6. Push to branch of MPS
# Note: This method will keep a changelog of releases.
# If we delete and newly checkout branches everytime,
# that will contain a changelog of changes.

cd ../

rm -rf templates tests validation

find . -name "*.bq" -type f | xargs git add
find . -name "*.avro" -type f | xargs git add
git commit -a -m "Auto-push from schema generation"

git checkout $MPS_BRANCH || git checkout -b $MPS_BRANCH

# Disallowing empty commits forces no-op on unchanged schemas
git cherry-pick --strategy-option theirs $DEV_BRANCH

git remote set-url origin git@github.com:mozilla-services/mozilla-pipeline-schemas.git
git push --force
