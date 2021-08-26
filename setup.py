#!/usr/bin/env python

# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys

from setuptools import find_packages, setup

if sys.argv[-1] == "publish":
    os.system("python setup.py sdist upload")
    sys.exit()

readme = open("README.md").read()

setup(
    name="mozilla-schema-generator",
    python_requires=">=3.6.0",
    version="0.4.2",
    description="Create full representations of schemas using the probe info service.",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="Mozilla Corporation",
    author_email="fx-data-dev@mozilla.org",
    url="https://github.com/mozilla/mozilla-schema-generator",
    packages=find_packages(include=["mozilla_schema_generator"]),
    package_dir={"mozilla-schema-generator": "mozilla_schema_generator"},
    entry_points={
        "console_scripts": [
            "mozilla-schema-generator=mozilla_schema_generator.__main__:main",
            "validate-bigquery=mozilla_schema_generator.validate_bigquery:validate",
        ]
    },
    include_package_data=True,
    install_requires=["click", "jsonschema", "pyyaml", "requests", "gitpython"],
    license="MIT",
    zip_safe=False,
    keywords="mozilla-schema-generator",
    classifiers=[
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
    ],
)
