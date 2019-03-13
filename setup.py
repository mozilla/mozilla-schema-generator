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
doclink = """
Documentation
-------------

The full documentation is at http://mozilla-schema-creator.rtfd.org."""
history = open('HISTORY.rst').read().replace('.. :changelog:', '')

setup(
    name='mozilla-schema-creator',
    version='0.1.0',
    description='Create full representations of schemas using the probe info service.',
    long_description=readme + '\n\n' + doclink + '\n\n' + history,
    author='Frank Bertsch',
    author_email='frank@mozilla.com',
    url='https://github.com/fbertsch/mozilla-schema-creator',
    packages=[
        'mozilla-schema-creator',
    ],
    package_dir={'mozilla-schema-creator': 'mozilla_schema_creator'},
    entry_points={
        'console_scripts': [
            'mozilla-schema-creator=mozilla_schema_creator.__main__:main',
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
    keywords='mozilla-schema-creator',
    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
    ],
)
