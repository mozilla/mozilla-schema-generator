#!/usr/bin/env python

import os
import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    sys.exit()

readme = open('README.md').read()

setup(
    name='mozilla-schema-generator',
    version='0.1.0',
    description='Create full representations of schemas using the probe info service.',
    long_description=readme,
    author='Frank Bertsch',
    author_email='frank@mozilla.com',
    url='https://github.com/fbertsch/mozilla-schema-generator',
    packages=[
        'mozilla-schema-generator',
    ],
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
