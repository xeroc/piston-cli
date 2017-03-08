#!/usr/bin/env python

from setuptools import setup
import sys

assert sys.version_info[0] == 3, "Piston requires Python > 3"

__VERSION__ = '0.5.0a1'

setup(
    name='piston-cli',
    version=__VERSION__,
    description='Command line tool to interface with the STEEM network',
    long_description=open('README.md').read(),
    download_url='https://github.com/xeroc/piston-cli/tarball/' + __VERSION__,
    author='Fabian Schuh',
    author_email='<Fabian@chainsquad.com>',
    maintainer='Fabian Schuh',
    maintainer_email='<Fabian@chainsquad.com>',
    url='http://cli.piston.rocks',
    keywords=['steem', 'library', 'api', 'rpc', 'cli'],
    packages=["pistoncli"],
    # https://github.com/pallets/flask/issues/1562
    zip_safe=False,
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
    ],
    entry_points={
        'console_scripts': [
            'piston = pistoncli.__main__:main',
        ],
    },
    install_requires=[
        "piston-lib>=0.5.0",
        "prettytable==0.7.2",
        "colorama==0.3.6",
    ],
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    include_package_data=True,
)
