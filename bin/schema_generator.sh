#!/bin/bash

# A script for generating schemas that are deployed into the pipeline. This
# script handles preprocessing, filtering, and transpilation of schemas as part
# of a pre-deployment scheme. The resulting schemas are pushed to a branch of
# mozilla-pipeline-schemas.
#
# Environment variables:
#   MPS_SSH_KEY_BASE64: A base64-encoded ssh secret key with permissions to push
#                       to mozilla-pipeline-schemas
#
# Example usage:
#   export MPS_SSH_KEY_BASE64=$(cat ~/.ssh/id_rsa | base64)
#   make build && make run
#
# TODO: Update schema mapping for validation
# TODO: Handle overwriting glean schemas
# TODO: Include Main Ping from schema generation
# TODO: What the heck to do with pioneer-study, a non-nested namespace

MPS_BRANCH_SOURCE="dev"
MPS_BRANCH_WORKING="generated-schemas-dev"
MPS_BRANCH_PUBLISH="generated-schemas"
MPS_SCHEMAS_DIR="schemas"

BASE_DIR="/app"


function setup_git_ssh() {
    # Configure the container for pushing to github

    if [[ -z "$MPS_SSH_KEY_BASE64" ]]; then
        echo "Missing secret key" 1>&2
        exit 1
    fi

    git config --global user.name "Generated Schema Creator"
    git config --global user.email "dataops+pipeline-schemas@mozilla.com"

    mkdir -p /app/.ssh

    echo "$MPS_SSH_KEY_BASE64" | base64 --decode > /app/.ssh/id_ed25519
    ssh-keyscan github.com > /app/.ssh/known_hosts # Makes the future git-push non-interactive

    chown -R "$(id -u):$(id -g)" "$HOME/.ssh"
    chmod 700 "$HOME/.ssh"
    chmod 700 "$HOME/.ssh/id_ed25519"
}

function setup_dependencies() {
    # Installs mozilla-schema-generator in a virtual environment

    virtualenv msg-venv
    # shellcheck disable=SC1091
    source msg-venv/bin/activate
    pip install -e ./mozilla-schema-generator
}

function clone_and_configure_mps() {
    # Checkout mozilla-pipeline-schemas and changes directory to prepare for
    # schema generation.

    rm -rf mozilla-pipeline-schemas

    git clone git@github.com:mozilla-services/mozilla-pipeline-schemas.git
    cd mozilla-pipeline-schemas/$MPS_SCHEMAS_DIR || exit
    git checkout $MPS_BRANCH_SOURCE

    git branch -D $MPS_BRANCH_WORKING
    git checkout -b $MPS_BRANCH_WORKING
}

function prepare_metadata() {
    # Assumes that all schemas under the current directory are valid JSON schema.

    local telemetry_metadata="metadata/telemetry-ingestion/telemetry-ingestion.1.schema.json"
    local structured_metadata="metadata/structured-ingestion/structured-ingestion.1.schema.json"

    find ./telemetry -type f -exec metadata_merge $telemetry_metadata {} ";"
    find . -path ./telemetry -prune -o -type f -exec metadata_merge $structured_metadata {} ";"
}

function filter_schemas() {
    # Remove metadata
    rm -rf metadata

    # Pioneer-study is not nested, remove it
    rm -rf pioneer-study

    # Replace newlines with backticks (hard to do with sed): cat | tr
    # Remove the last backtick; it's the file-ending newline: rev | cut | rev
    # Replace backticks with "\|" (can't do that with tr): sed
    # Find directories that don't match any of the regex expressions: find
    # Remove them: rm
    < /app/mozilla-schema-generator/bin/allowlist tr '\n' '`' | \
        rev | cut -c 2- | rev | \
        sed -e 's/`/\\\\|/g' | \
        xargs -I % find . -type f -regextype sed -not -regex '.*/\(%\|metadata/\)/.*' | grep ".bq" | \
        xargs rm -rf
}

function commit_schemas() {
    # This method will keep a changelog of releases. If we delete and newly
    # checkout branches everytime, that will contain a changelog of changes.
    # Assumes the current directory is the root of the repository

    find . -name "*.bq" -type f -exec git add {} +
    git checkout ./*.schema.json
    git commit -a -m "Interim Commit"

    git checkout $MPS_BRANCH_PUBLISH || git checkout -b $MPS_BRANCH_PUBLISH

    # Keep only the schemas dir
    find .  -mindepth 1 -maxdepth 1 -not -name .git -exec rm -rf {} +
    git checkout $MPS_BRANCH_WORKING -- schemas
    git commit -a -m "Auto-push from schema generation"
}

function main() {
    cd $BASE_DIR || exit

    # -1. Setup ssh key and git config
    setup_git_ssh

    # 0. Install dependencies
    setup_dependencies

    # 1. Pull in all schemas from MPS
    clone_and_configure_mps
    # CWD: /app/mozilla-pipeline-schemas

    # 2. Remove all non-json schemas (e.g. parquet)
    find . -not -name "*.schema.json" -type f -exec rm {} +

    # 3. Generate new schemas
    mozilla-schema-generator generate-glean-ping --out-dir . --pretty

    # 4. Add metadata to all json schemas, drop metadata schemas
    prepare_metadata

    # 5. Add transpiled BQ schemas
    find . -type f -name "*.schema.json"|while read -r fname; do
        bq_out=${fname/schema.json/bq}
        jsonschema-transpiler --type bigquery "$fname" > "$bq_out"
    done

    # 5b. Keep only allowed schemas
    filter_schemas

    # 6. Push to branch of MPS
    cd ../ || exit
    commit_schemas
    git push --force
}

main