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

set -exuo pipefail

MPS_REPO_URL=${MPS_REPO_URL:-"git@github.com:mozilla-services/mozilla-pipeline-schemas.git"}
MPS_BRANCH_SOURCE=${MPS_BRANCH_SOURCE:-"master"}
MPS_BRANCH_PUBLISH=${MPS_BRANCH_PUBLISH:-"test-generated-schemas"}

MPS_BRANCH_WORKING="local-working-branch"
MPS_SCHEMAS_DIR="schemas"
BASE_DIR="/app"
DISALLOWLIST="$BASE_DIR/mozilla-schema-generator/disallowlist"
ALIASES_PATH="$BASE_DIR/mozilla-schema-generator/aliases.json"
COMMON_PINGS_PATH="$BASE_DIR/mozilla-schema-generator/common_pings.json"

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

    # add private key to the ssh agent to prompt for password once
    eval "$(ssh-agent)"
    ssh-add
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

function filter_schemas() {
    # Remove BigQuery schemas that are in the disallow list
    find . -name '*.bq' | grep -f $DISALLOWLIST | xargs rm -f
}

function create_changelog() {
    # Generate output for referencing to the changeset in the source branch.
    # Useful references for --format and --pretty
    # https://stackoverflow.com/questions/25563455/how-do-i-get-last-commit-date-from-git-repository
    # https://stackoverflow.com/questions/1441010/the-shortest-possible-output-from-git-log-containing-author-and-date
    # https://git-scm.com/docs/git-log/1.8.0#git-log---daterelativelocaldefaultisorfcshortraw
    local start_date
    # NOTES: Since this function is looking at commit dates (such as rebases),
    # it's best to enforce squash/rebase commits onto the master branch. If this
    # isn't enforced, it's possible to miss out on certain commits to the
    # generated branch. Another solution is to generate a tag on master before
    # the generator is run. However, the heuristic of using the latest commit
    # date works well enough.
    start_date=$(git log "${MPS_BRANCH_PUBLISH}" -1 --format=%cd --date=iso)
    git log "${MPS_BRANCH_SOURCE}" \
        --since="$start_date" \
        --pretty=format:"%h%x09%cd%x09%s" \
        --date=iso
}

function commit_schemas() {
    # This method will keep a changelog of releases. If we delete and newly
    # checkout branches everytime, that will contain a changelog of changes.
    # Assumes the current directory is the root of the repository.
    # Note that in this step we throw out all the temporary modifications we've
    # made to the JSON schemas.
    find . -name "*.bq" -type f -exec git add {} +
    git checkout ./*.schema.json

    # Add Glean JSON schemas with generic schema
    mozilla-schema-generator generate-glean-pings --out-dir $MPS_SCHEMAS_DIR --pretty --generic-schema --mps-branch $MPS_BRANCH_SOURCE
    find . -name "*.schema.json" -type f -exec git add {} +

    git commit -a -m "Interim Commit"

    git checkout "$MPS_BRANCH_PUBLISH" || git checkout -b "$MPS_BRANCH_PUBLISH"

    # Keep only the schemas dir
    find . -mindepth 1 -maxdepth 1 -not -name .git -exec rm -rf {} +
    git checkout $MPS_BRANCH_WORKING -- schemas
    git commit --all \
        --message "Auto-push from schema generation [ci skip]" \
        --message "$(create_changelog)" \
        || echo "Nothing to commit"
}

function main() {
    cd $BASE_DIR

    # Setup ssh key and git config
    setup_git_ssh

    # Pull in all schemas from MPS and change directory
    clone_and_configure_mps

    # Generate concrete JSON schemas that contain per-probe fields.
    # These are used only as the basis for generating BQ schemas;
    # we publish JSON schemas exactly as they appear in the source branch so
    # that the pipeline doesn't rely on per-probe types when validating pings.
    # For Glean pings, we copy the generic Glean schema into place later on.
    mozilla-schema-generator generate-main-ping --out-dir ./telemetry --mps-branch $MPS_BRANCH_SOURCE
    mozilla-schema-generator generate-common-pings --common-pings-config $COMMON_PINGS_PATH --mps-branch $MPS_BRANCH_SOURCE --out-dir ./telemetry
    mozilla-schema-generator generate-glean-pings --mps-branch $MPS_BRANCH_SOURCE --out-dir .

    # Remove all non-json schemas (e.g. parquet)
    find . -not -name "*.schema.json" -type f -exec rm {} +

    # Add metadata fields to all json schemas
    # schema directory structure is enforced by regex at compile-time
    # shellcheck disable=SC2044
    for schema in $(find . -name "*.schema.json" -type f); do
        metadata_merge metadata/ "$schema"
    done

    # Add transpiled BQ schemas
    find . -type f -name "*.schema.json" | while read -r fname; do
        # This schema is AWS-specific, fails transpilation, and should be ignored
        if [[ $fname =~ metadata/sources ]] ; then
            continue
        fi
        bq_out=${fname/schema.json/bq}
        mkdir -p $(dirname "$bq_out")
        jsonschema-transpiler \
            --resolve drop \
            --type bigquery \
            --normalize-case \
            --force-nullable \
            --tuple-struct \
                "$fname" > "$bq_out"
    done

    # Keep only allowed schemas
    filter_schemas

    # Copy aliased BQ schemas into place
    alias_schemas $ALIASES_PATH .

    # Push to branch of MPS
    cd ../
    commit_schemas
    git push || git push --set-upstream origin "$MPS_BRANCH_PUBLISH"
}

main "$@"
