#!/usr/bin/env python
from distutils.core import setup
from puflib import version

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

# stamp the package prior to installation
version.stamp_directory(os.path.join(os.getcwd(), 'puflib'))

setup(
    name='puflib',
    version=version.get_version(),
    description='Library for Emulating Physically Unclonable Functions',
    author='Gregory N. Schmit',
    author_email='schmitgreg@gmail.com',
    url='https://github.com/gregschmit/puflib',
    packages=['puflib',],
    include_package_data=True,
    package_data={'puflib': ['VERSION_STAMP']},
    install_requires=['numpy',],
)
