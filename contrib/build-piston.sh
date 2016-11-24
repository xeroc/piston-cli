#!/bin/bash

source environment.sh

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
# $PYTHON "C:/pyinstaller/pyinstaller.py" --noconfirm --ascii --paths=$PYHOME\Lib\site-packages -c -F piston.spec

# build NSIS installer
wine "$WINEPREFIX/drive_c/Program Files (x86)/NSIS/makensis.exe" /DPRODUCT_VERSION=$VERSION piston.nsi

cd dist
mv piston-setup.exe $NAME_ROOT-$VERSION-setup.exe
mv piston $NAME_ROOT-$VERSION
zip -r $NAME_ROOT-$VERSION.zip $NAME_ROOT-$VERSION
cd ..

echo "Done."
