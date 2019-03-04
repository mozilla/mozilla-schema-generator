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

readme = open('README.rst').read()
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
    package_dir={'mozilla-schema-creator': 'mozilla-schema-creator'},
    include_package_data=True,
    install_requires=[
    ],
    license='MIT',
    zip_safe=False,
    keywords='mozilla-schema-creator',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
)
