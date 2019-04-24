#!/usr/bin/env python

# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys

from setuptools import setup, find_packages


if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    sys.exit()

readme = open('README.md').read()

setup(
    name='mozilla-schema-generator',
    version='0.1.3',
    description='Create full representations of schemas using the probe info service.',
    long_description=readme,
    author='Frank Bertsch',
    author_email='frank@mozilla.com',
    url='https://github.com/mozilla/mozilla-schema-generator',
    packages=find_packages(include=['mozilla_schema_generator']),
    package_dir={'mozilla-schema-generator': 'mozilla_schema_generator'},
    entry_points={
        'console_scripts': [
            'mozilla-schema-generator=mozilla_schema_generator.__main__:main',
        ],
    },
    include_package_data=True,
    install_requires=[
        'requests',
        'click',
        'pyyaml',
    ],
    license='MIT',
    zip_safe=False,
    keywords='mozilla-schema-generator',
    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
    ],
)
