#!/bin/bash

source mozilla-schema-generator/bin/schema_generator.sh
# -e causes the container to exit immediately
set +e
setup_git
setup_mps
mozilla-schema-generator/bin/test_validate main  >> schema.diff
sed -n '/---/,$p' < tmp.log > schema.diff
