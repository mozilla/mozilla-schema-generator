#!/bin/bash

# TODO: Update schema mapping for validation
# TODO: Handle overwriting glean schemas
# TODO: Include Main Ping from schema generation
# TODO: What the heck to do with pioneer-study, a non-nested namespace

# -1: Setup ssh key and git config

if [[ -z $MOZILLA_PIPELINE_SCHEMAS_SECRET_GIT_SSHKEY_BASE64_ENCODED ]]; then
    echo "Missing secret key" 1>&2
    exit 1
fi

if [[ -z $USER_ID ]]; then
    echo "Missing User ID" 1>&2
    exit 1
fi

git config --global user.name "Generated Schema Creator"
git config --global user.email "dataops+pipeline-schemas@mozilla.com"

mkdir -p /app/.ssh

echo $MOZILLA_PIPELINE_SCHEMAS_SECRET_GIT_SSHKEY_BASE64_ENCODED | base64 --decode > /app/.ssh/id_ed25519
ssh-keyscan github.com > /app/.ssh/known_hosts # Makes the future git-push non-interactive

chown -R $USER_ID:$USER_ID ~/.ssh
chmod 700 "$HOME/.ssh"
chmod 700 "$HOME/.ssh/id_ed25519"

MASTER_BRANCH="dev" # Branch we'll work on - this should have the most up-to-date schemas
DEV_BRANCH="generated-schemas-dev" # Branch we'll work on
MPS_BRANCH="generated-schemas" # Branch we'll push to

SCHEMAS_DIR="schemas"
BASE_DIR="/app"

cd $BASE_DIR

# 0. Install dependencies

cargo install jsonschema-transpiler

virtualenv mgs-venv 
source mgs-venv/bin/activate
pip install -e ./mozilla-schema-generator

# 1. Pull in all schemas from MPS
rm -rf mozilla-pipeline-schemas

git clone https://www.github.com/mozilla-services/mozilla-pipeline-schemas.git
cd mozilla-pipeline-schemas/$SCHEMAS_DIR
git checkout $MASTER_BRANCH

git branch -D $DEV_BRANCH
git checkout -b $DEV_BRANCH

# 2. Remove all non-json schemas (e.g. parquet)

find . -not -name "*.schema.json" -type f | xargs rm

# 3. Generate new schemas

mozilla-schema-generator generate-glean-ping --out-dir . --pretty
#mozilla-schema-generator generate-main-ping --out-dir ./main-ping --pretty --split

# 4. Add metadata to all json schemas, drop metadata schemas

metadata_dir="metadata"
telemetry_metadata="$metadata_dir/telemetry-ingestion/telemetry-ingestion.1.schema.json"
structured_metadata="$metadata_dir/structured-ingestion/structured-ingestion.1.schema.json"

find ./telemetry -type f -exec metadata_merge $telemetry_metadata {} ";"
find . -path ./telemetry -prune -o -type f -exec metadata_merge $structured_metadata {} ";"

rm -rf $metadata_dir

# 5. Add transpiled BQ schemas

find . -type f|while read fname; do
    BQ_OUT=${fname/schema.json/bq}
    jsonschema-transpiler --type bigquery $fname | jq '.fields' > $BQ_OUT
done

# 5b. Keep only allowed schemas

# Pioneer-study is not nested, remove it
rm -rf pioneer-study

# Replace newlines with backticks (hard to do with sed): cat | tr
# Remove the last backtick; it's the file-ending newline: rev | cut | rev
# Replace backticks with "\|" (can't do that with tr): sed
# Find directories that don't match any of the regex expressions: find
# Remove them: rm
cat /app/mozilla-schema-generator/bin/allowlist | tr '\n' '`' | rev | cut -c 2- | rev | sed -e 's/`/\\\\|/g' | xargs -I % find . -type f -regextype sed -not -regex '.*/\(%\|metadata/\)/.*' | grep ".bq" | xargs rm -rf


# 6. Push to branch of MPS
# Note: This method will keep a changelog of releases.
# If we delete and newly checkout branches everytime,
# that will contain a changelog of changes.

cd ../

find . -name "*.bq" -type f | xargs git add
git commit -m "Interim Commit"
git stash

git checkout $MPS_BRANCH || git checkout -b $MPS_BRANCH

# Keep only the schemas dir
find .  -mindepth 1 -maxdepth 1 -not -name .git | xargs rm -rf
git checkout $DEV_BRANCH -- schemas
git commit -a -m "Auto-push from schema generation"

git remote set-url origin git@github.com:mozilla-services/mozilla-pipeline-schemas.git
git push --force
