home = "tmp/piston"

a = Analysis([
        home + '/cli.py'
    ],
    pathex=[
        "C:\\Python34\\libs\\",
        "C:\\Python34\\Lib\\site-packages",
        home,
    ],
    datas=[
        # (home + '/piston/web/templates', 'web/templates'),
        # (home + '/piston/web/static', 'web/static'),
    ],
    hiddenimports=[
        "piston.__main__",
        # "piston.web.__init__",
        "scrypt", "_scrypt",
    ]
)
pyz = PYZ(
    a.pure,
    a.zipped_data
)

exe = EXE(
    pyz,
    a.scripts,
    ##########
    #a.binaries,
    #a.datas,
    ##########
    exclude_binaries=True,
    name='piston.exe',
    debug=False,
    strip=None,
    upx=False,
    #icon=home+'icons/piston.ico',
    console=True
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=None,
    upx=True,
    debug=False,
    # icon=home+'icons/piston.ico',
    console=True,
    name=os.path.join('dist', 'piston')
)

# vim: ts=4 sw=4 expandtab ft=python
