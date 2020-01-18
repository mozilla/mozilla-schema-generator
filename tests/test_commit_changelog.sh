#!/bin/bash
# A script for testing the functionality of changelog information in generated
# schemas. The output of the this command must be checked manually, and this
# script must be configured to commit with your identity.

# To run this script, copy and paste the commands in the heredoc into your shell
: << EOF
export MPS_SSH_KEY_BASE64=$(cat ~/.ssh/id_rsa | base64)

make build && \
docker-compose run --entrypoint /bin/bash app \
    mozilla-schema-generator/tests/test_commit_changelog.sh
EOF

set -exuo pipefail

# 2020-01-07 to 2020-01-08, chosen due to the number of commits
initial_commit=f28259d4d6995a5af8ec3d850dc432a43baca906
last_commit=b69699673bf01df9d357bd3e2f4dbde9fe6ec726

# $ git log f28259d...b696996 --oneline
# b696996 Make the $id for main ping schema show version as "4"
# a56043b Add page for china build to activity stream impression_stats
# 6b9c323 Allow negative sessionLengths and event timestamps
# 29b042f Allow for old-style ping_type in glean
# d093483 Add changelog entry
# dc87e27 Make glean ping_type kebab

export MPS_SSH_KEY_BASE64=${MPS_SSH_KEY_BASE64?key must be set}
export MPS_BRANCH_SOURCE=${initial_commit}
export MPS_BRANCH_PUBLISH="test-generated-schemas-changelog"
MPS_GIT_PATH=/app/mozilla-pipeline-schemas

# initialize the testing branch using the generator script
cd "$(dirname "$0")/.."
bin/schema_generator.sh

# now, update the timestamp of the commit to be the same as the initial commit
# https://stackoverflow.com/questions/454734/how-can-one-change-the-timestamp-of-an-old-commit-in-git

# directory is derived from logic in schema_generator
pushd ${MPS_GIT_PATH}
git checkout ${MPS_BRANCH_PUBLISH}
GIT_COMMITTER_DATE=$(git log ${initial_commit} -1 --pretty=%cd --date=iso) \
    git commit --amend --no-edit
# now the commit hash has changed, so we must force push
git push -f
popd

# run the generator again and check the log
export MPS_BRANCH_SOURCE=${last_commit}
bin/schema_generator.sh

# check the results
pushd ${MPS_GIT_PATH}
git log ${MPS_BRANCH_PUBLISH} -1
