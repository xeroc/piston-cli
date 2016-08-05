#!/bin/bash

PYHOME=c:/python34
WINEPREFIX=~/.wine/

# Please update these links carefully, some versions won't work under Wine
PYTHON_URL=https://www.python.org/ftp/python/3.4.0/python-3.4.0.msi
PYWIN32_URL=http://downloads.sourceforge.net/project/pywin32/pywin32/Build%20220/pywin32-220.win32-py3.4.exe
PYINSTALLER_URL=https://github.com/pyinstaller/pyinstaller/releases/download/v3.2/PyInstaller-3.2.zip
NSIS_URL=http://downloads.sourceforge.net/project/nsis/NSIS%203/3.0/nsis-3.0-setup.exe
PYCRYPTO=http://www.voidspace.org.uk/python/pycrypto-2.6.1/pycrypto-2.6.1.win32-py3.4.exe

# Let's begin!
cd `dirname $0`
set -e

# Clean up Wine environment
echo "Cleaning $WINEPREFIX"
rm -rf $WINEPREFIX
echo "done"

wine 'wineboot'
winetricks win7

echo "Cleaning tmp"
rm -rf tmp
mkdir -p tmp
echo "done"

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

# add dlls needed for pyinstaller:
cp $WINEPREFIX/drive_c/windows/system32/msvcp90.dll $WINEPREFIX/drive_c/Python34/
cp $WINEPREFIX/drive_c/windows/system32/msvcm90.dll $WINEPREFIX/drive_c/Python34/

# Install from pip
wine $PYHOME/Scripts/pip.exe install pefile steem-piston
