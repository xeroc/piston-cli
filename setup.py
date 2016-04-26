#!/usr/bin/env python

from setuptools import setup

VERSION = '0.0.2'

setup(name='steem-piston',
      version=VERSION,
      description='Command line tool to interface with the STEEM network',
      long_description=open('README.md').read(),
      download_url='https://github.com/xeroc/piston/tarball/' + VERSION,
      author='Fabian Schuh',
      author_email='<Fabian@BitShares.eu>',
      maintainer='Fabian Schuh',
      maintainer_email='<Fabian@BitShares.eu>',
      url='http://www.github.com/xeroc/piston',
      keywords=['steem', 'library', 'api', 'rpc', 'cli'],
      packages=["piston"],
      classifiers=['License :: OSI Approved :: MIT License',
                   'Operating System :: OS Independent',
                   'Programming Language :: Python :: 3',
                   'Development Status :: 3 - Alpha',
                   'Intended Audience :: Developers',
                   ],
      entry_points={
          'console_scripts': [
              'piston = piston.__main__:main',
          ],
      },
      install_requires=["steem",
                        "python-frontmatter",
                        ],
      )
