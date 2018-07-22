#!/usr/bin/env python

from distutils.core import setup

setup(
    name='puflib',
    version='0.1',
    description='Library for Emulating Physically Unclonable Functions',
    author='Gregory N. Schmit',
    author_email='schmitgreg@gmail.com',
    url='https://github.com/gregschmit/puflib',
    install_requires=['numpy',],
    py_modules=['puflib',],
)
