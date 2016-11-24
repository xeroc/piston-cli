#!/bin/bash

source environment.sh

# Let's begin!
cd `dirname $0`
set -e

# Clean up Wine environment
echo "Cleaning $WINEPREFIX"
rm -rf $WINEPREFIX
echo "done"

# Cleanup temp
echo "Cleaning tmp"
rm -rf tmp
mkdir -p tmp
echo "done"

wine 'wineboot'
winetricks win7

cd tmp

# Install Python
wget -O python.msi "$PYTHON_URL"
wine msiexec /q /i python.msi

# Install PyWin32
wget -O pywin32.exe "$PYWIN32_URL"
wine pywin32.exe

# Install pyinstaller
wget -O pyinstaller.zip "$PYINSTALLER_URL"
unzip pyinstaller.zip
mv PyInstaller-3.2 $WINEPREFIX/drive_c/pyinstaller

# Install NSIS installer
wget -O nsis.exe "$NSIS_URL"
wine nsis.exe

# Install PyCrypto
wget -O pycrypto.exe "$PYCRYPTO"
wine pycrypto.exe

# Install OpenSSL
wget -O openssl.exe "$OPENSSL"
wine openssl.exe

# piston
git clone -b $BRANCH $GIT_URL piston
# wine $PYHOME/Scripts/pip.exe install -r requirements-web.txt --upgrade

# Libraries
wine $PYHOME/Scripts/pip.exe install https://github.com/xeroc/python-graphenelib/archive/develop.zip#egg=graphenelib --upgrade
wine $PYHOME/Scripts/pip.exe install https://github.com/xeroc/python-steem/archive/develop.zip#egg=steem --upgrade
wine $PYHOME/Scripts/pip.exe install pefile steem-piston
wine $PYHOME/Scripts/pip.exe install https://pypi.python.org/packages/7d/fc/3e65f21be05f5f1bafa8f2262fea474c6dd84cc7dc226d453dd488675305/scrypt-0.7.1-cp34-none-win32.whl

# add dlls needed for pyinstaller:
cp "$WINEPREFIX/drive_c/windows/system32/msvcp90.dll" "$WINEPREFIX/drive_c/Python34/"
cp "$WINEPREFIX/drive_c/windows/system32/msvcm90.dll" "$WINEPREFIX/drive_c/Python34/"
cp "$WINEPREFIX/drive_c/./Program Files (x86)/GnuWin32/bin/libeay32.dll" "$WINEPREFIX/drive_c/Python34/"

# Install from pip

echo "###########################"
echo "Preparations done"
echo "###########################"
