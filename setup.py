#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

# To use a consistent encoding
from codecs import open
from os import path

from setuptools import find_packages, setup

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='haec-emulator',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version='0.0.2',

    description='Network emulator on HEAC playground',
    long_description=long_description,

    # The project's main homepage.
    url='https://github.com/stevelorenz/haec-emulator',

    # Author details
    author='Zuo Xiang',
    author_email='xianglinks@gmail.com',

    # Choose your license
    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',
        'Environment :: MaxiNet',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Natural Language :: English'
    ],

    # What does your project relate to?
    keywords='Network Emulator',

    packages=find_packages(
        exclude=['venv', 'share', 'examples', 'script']),

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    # install_requires=['peppercorn'],

    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[dev,test]
    # extras_require={
    # 'dev': ['check-manifest'],
    # 'test': ['coverage'],
    # },

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    # entry_points={
    # 'console_scripts': [
    # 'sfc-ostack = sfcostack.cli:cli',
    # ],
    # },
)
