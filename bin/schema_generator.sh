#!/bin/bash

# A script for generating schemas that are deployed into the pipeline. This
# script handles preprocessing, filtering, and transpilation of schemas as part
# of a pre-deployment scheme. The resulting schemas are pushed to a branch of
# mozilla-pipeline-schemas.
#
# Environment variables:
#   MPS_SSH_KEY_BASE64: A base64-encoded ssh secret key with permissions to push
#                       to mozilla-pipeline-schemas
#   MPS_REPO_URL:       The URL to the mozilla-pipeline-schemas repository
#   MPS_BRANCH_SOURCE:  The source branch for generating schemas e.g. master
#   MPS_BRANCH_PUBLISH: The destination branch for publishing schemas
#                       e.g. generated-schemas
#
# Example usage:
#   export MPS_SSH_KEY_BASE64=$(cat ~/.ssh/id_rsa | base64)
#   make build && make run
#
# TODO: Update schema mapping for validation
# TODO: Handle overwriting glean schemas
# TODO: Include Main Ping from schema generation
# TODO: What the heck to do with pioneer-study, a non-nested namespace

set -exuo pipefail

MPS_REPO_URL=${MPS_REPO_URL:-"git@github.com:mozilla-services/mozilla-pipeline-schemas.git"}
MPS_BRANCH_SOURCE=${MPS_BRANCH_SOURCE:-"master"}
MPS_BRANCH_PUBLISH=${MPS_BRANCH_PUBLISH:-"test-generated-schemas"}

MPS_BRANCH_WORKING="local-working-branch"
MPS_SCHEMAS_DIR="schemas"
BASE_DIR="/app"
ALLOWLIST="$BASE_DIR/mozilla-schema-generator/allowlist"


function setup_git_ssh() {
    # Configure the container for pushing to github

    if [[ -z "$MPS_SSH_KEY_BASE64" ]]; then
        echo "Missing secret key" 1>&2
        exit 1
    fi

    git config --global user.name "Generated Schema Creator"
    git config --global user.email "dataops+pipeline-schemas@mozilla.com"

    mkdir -p "$HOME/.ssh"

    echo "$MPS_SSH_KEY_BASE64" | base64 --decode > /app/.ssh/id_ed25519
    # Makes the future git-push non-interactive
    ssh-keyscan github.com > /app/.ssh/known_hosts

    chown -R "$(id -u):$(id -g)" "$HOME/.ssh"
    chmod 700 "$HOME/.ssh"
    chmod 700 "$HOME/.ssh/id_ed25519"
}

function setup_dependencies() {
    # Installs mozilla-schema-generator in a virtual environment

    python3 -m venv msg-venv
    # shellcheck disable=SC1091
    source msg-venv/bin/activate
    pip install -e ./mozilla-schema-generator
}

function clone_and_configure_mps() {
    # Checkout mozilla-pipeline-schemas and changes directory to prepare for
    # schema generation.

    [[ -d mozilla-pipeline-schemas ]] && rm -r mozilla-pipeline-schemas

    git clone "$MPS_REPO_URL"
    cd mozilla-pipeline-schemas/$MPS_SCHEMAS_DIR
    git checkout "$MPS_BRANCH_SOURCE"
    git checkout -b $MPS_BRANCH_WORKING
}

function prepare_metadata() {
    local telemetry_metadata="metadata/telemetry-ingestion/telemetry-ingestion.1.schema.json"
    local structured_metadata="metadata/structured-ingestion/structured-ingestion.1.schema.json"

    find ./telemetry -name "*.schema.json" -type f \
        -exec metadata_merge $telemetry_metadata {} ";"
    find . -path ./telemetry -prune -o -name "*.schema.json" -type f \
        -exec metadata_merge $structured_metadata {} ";"
}

function filter_schemas() {
    # Remove metadata schemas
    rm -rf metadata

    # Pioneer-study is not nested, remove it
    rm -rf pioneer-study

    # Remove BigQuery schemas that are not in the allowlist
    find . -name '*.bq' | grep -v -f $ALLOWLIST | xargs rm -f
}

function commit_schemas() {
    # This method will keep a changelog of releases. If we delete and newly
    # checkout branches everytime, that will contain a changelog of changes.
    # Assumes the current directory is the root of the repository
    find . -name "*.bq" -type f -exec git add {} +
    git checkout ./*.schema.json

    # Add Glean JSON schemas with generic schema
    mozilla-schema-generator generate-glean-pings --out-dir $MPS_SCHEMAS_DIR --pretty --generic-schema
    find . -name "*.schema.json" -type f -exec git add {} +

    git commit -a -m "Interim Commit"

    git checkout "$MPS_BRANCH_PUBLISH" || git checkout -b "$MPS_BRANCH_PUBLISH"

    # Keep only the schemas dir
    find . -mindepth 1 -maxdepth 1 -not -name .git -exec rm -rf {} +
    git checkout $MPS_BRANCH_WORKING -- schemas
    git commit -a -m "Auto-push from schema generation [ci skip]" || echo "Nothing to commit"
}

function main() {
    cd $BASE_DIR

    # Setup ssh key and git config
    setup_git_ssh

    # Install dependencies
    setup_dependencies

    # Pull in all schemas from MPS and change directory
    clone_and_configure_mps

    # Generate new schemas
    mozilla-schema-generator generate-glean-pings --out-dir .

    # Overwrite schemas in schemas dir
    cp -TRv $BASE_DIR/mozilla-schema-generator/schemas/ ./

    # Remove all non-json schemas (e.g. parquet)
    find . -not -name "*.schema.json" -type f -exec rm {} +

    # Add metadata to all json schemas, drop metadata schemas
    prepare_metadata

    # Add transpiled BQ schemas
    find . -type f -name "*.schema.json" | while read -r fname; do
        bq_out=${fname/schema.json/bq}
        # Snake case untrustedModules for bug 1565074
        bq_out=${bq_out//untrustedModules/untrusted_modules}
        mkdir -p $(dirname "$bq_out")
        jsonschema-transpiler --resolve drop --type bigquery --normalize-case "$fname" > "$bq_out"
    done

    # Keep only allowed schemas
    filter_schemas

    # Push to branch of MPS
    cd ../
    commit_schemas
    git push
}

main "$@"
