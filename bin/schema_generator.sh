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
#   MPS_VALIDATE_BQ:    Set to 'false' to disable the validation step
#
# Example usage:
#   export MPS_SSH_KEY_BASE64=$(cat ~/.ssh/id_rsa | base64)
#   make build && make run

set -e
set -x

MPS_REPO_URL=${MPS_REPO_URL:-"git@github.com:mozilla-services/mozilla-pipeline-schemas.git"}
MPS_BRANCH_SOURCE=${MPS_BRANCH_SOURCE:-"master"}
MPS_BRANCH_PUBLISH=${MPS_BRANCH_PUBLISH:-"test-generated-schemas"}
MPS_VALIDATE_BQ=${MPS_VALIDATE_BQ:-"true"}
BIN="$(realpath ${BASH_SOURCE%/*})"


function setup_git() {
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

function setup_mps() {
    # Checkout mozilla-pipeline-schemas and changes directory to prepare for
    # schema generation.
    pushd .

    [[ -d mozilla-pipeline-schemas ]] && rm -rf mozilla-pipeline-schemas
    git clone "$MPS_REPO_URL"
    cd mozilla-pipeline-schemas
    git fetch --all
    git checkout "$MPS_BRANCH_PUBLISH"
    git checkout "$MPS_BRANCH_SOURCE"

    popd
}

function validated_generate_commit() {
    # Generate and commit schemas from the source branch into the publish
    # branch, and validate the resulting commit against a base branch with
    # generated schemas.
    local mps_root=$1
    local mps_branch_source=$2
    local mps_branch_publish=$3
    local mps_branch_base=${4:-$mps_branch_publish}
    local mps_branch_temp="base-revision"
    # shellcheck disable=SC1090
    source "${BIN}/generate_commit"

    # We copy the base branch into a new temporary head, since it could point to
    # the publish branch. Because the publish branch is the branch with the new
    # commits, we can't simply reuse the branch head since it will move.
    pushd .
    cd "$mps_root"
    git checkout "$mps_branch_publish"
    git checkout "$mps_branch_base"
    git branch -D "$mps_branch_temp" || :
    git checkout -b "$mps_branch_temp"
    popd

    # Generate schemas, commits results to the publish branch
    generate_commit "$mps_root" "$mps_branch_source" "$mps_branch_publish"

    if [ "$MPS_VALIDATE_BQ" != "false" ]; then
        validate-bigquery local-validation \
            --head "$mps_branch_publish" \
            --base "$mps_branch_temp"
    fi
}

function main() {
    # show the current package for mozilla-schema-generator
    echo $(pip freeze | grep mozilla-schema-generator)

    pushd .
    # the base directory in the docker container
    cd /app
    setup_git
    setup_mps

    validated_generate_commit \
        /app/mozilla-pipeline-schemas \
        "$MPS_BRANCH_SOURCE" \
        "$MPS_BRANCH_PUBLISH"

    cd mozilla-pipeline-schemas
    git push || git push --set-upstream origin "$MPS_BRANCH_PUBLISH"
    popd
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
