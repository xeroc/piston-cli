#!/bin/bash

$BRANCH="develop"
WINEPREFIX=~/.wine/
PYHOME=c:/Python34
PYTHON="wine $PYHOME/python.exe -OO -B"

cd `dirname $0`
set -e

cd tmp

# GIT repository found, update it
echo "Pull"
cd piston
git checkout $BRANCH
git pull

$PYTHON setup.py install

VERSION=`git describe --tags`
echo "Last commit: $VERSION"

cd ..

rm -rf $WINEPREFIX/drive_c/piston
cp -r piston $WINEPREFIX/drive_c/piston

cd ..

rm -rf dist/ build/

# Nothing works if we keep the piston.py file unchainged ..
cp tmp/piston/piston.py tmp/piston/cli.py

# build standalone version
$PYTHON "C:/pyinstaller/pyinstaller.py" --noconfirm --ascii --paths=$PYHOME\Lib\site-packages -c piston.spec
$PYTHON "C:/pyinstaller/pyinstaller.py" --noconfirm --ascii --paths=$PYHOME\Lib\site-packages -c -F piston.spec

echo "Done."
