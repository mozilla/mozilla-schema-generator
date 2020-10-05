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

set -e
set -x

MPS_REPO_URL=${MPS_REPO_URL:-"git@github.com:mozilla-services/mozilla-pipeline-schemas.git"}
MPS_BRANCH_SOURCE=${MPS_BRANCH_SOURCE:-"master"}
MPS_BRANCH_PUBLISH=${MPS_BRANCH_PUBLISH:-"test-generated-schemas"}
MPS_BRANCH_WORKING="local-working-branch"


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

    [[ -d mozilla-pipeline-schemas ]] && rm -r mozilla-pipeline-schemas
    git clone "$MPS_REPO_URL"
    cd mozilla-pipeline-schemas
    git checkout "$MPS_BRANCH_SOURCE"
    git checkout -b $MPS_BRANCH_WORKING

    popd
}

function main() {
    # the base directory in the docker container
    cd /app
    setup_git
    setup_mps

    # shellcheck disable=SC1090
    source "${BASH_SOURCE%/*}/transpile_commit"

    generate_schemas \
        ./mozilla-pipeline-schemas \
        "$MPS_BRANCH_SOURCE"

    commit_schemas \
        ./mozilla-pipeline-schemas \
        "$MPS_BRANCH_SOURCE"
        "$MPS_BRANCH_PUBLISH"

    git push || git push --set-upstream origin "$MPS_BRANCH_PUBLISH"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
