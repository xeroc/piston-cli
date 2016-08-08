# -*- mode: python -*-

a = Analysis(['tmp/piston/cli.py'],
             pathex=[
                 "C:\\Python34\\libs\\",
                 "C:\\Python34\\Lib\\site-packages",
                 "tmp\\piston",
             ],
#             datas=[('piston/templates', '.')],
             hiddenimports=[
                 "piston.__main__",
                 "scrypt", "_scrypt",
             ])
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(pyz,
          a.scripts,
          #######################
          #a.binaries,
          #a.zipfiles,
          #a.datas,
          #######################
          exclude_binaries=True,
          #######################
          name='piston',
          debug=False,
          strip=False,
          upx=True,
          console=True)
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='piston')
