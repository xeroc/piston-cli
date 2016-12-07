#!/bin/bash

source environment.sh

# Let's begin!
cd `dirname $0`
set -e

# Install Steem
wine $PYHOME/Scripts/pip.exe install https://github.com/xeroc/python-steem/archive/develop.zip#egg=steem --upgrade
