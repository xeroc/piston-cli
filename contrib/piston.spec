home = "tmp\\piston"

a = Analysis(
    ['tmp/piston/cli.py'],
    pathex=[
        "C:\\Python34\\libs\\",
        "C:\\Python34\\Lib\\site-packages",
        home,
    ],
    datas=[
        (home + '/piston/templates', 'templates'),
        (home + '/piston/static', 'static'),
    ],
    hiddenimports=[
        "piston.__main__",
        "scrypt", "_scrypt",
#        "piston.web",
    ]
)
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(
    pyz,
    a.scripts,
    #######################
    # a.binaries,
    # a.zipfiles,
    # a.datas,
    #######################
    exclude_binaries=True,
    #######################
    name='piston',
    debug=False,
    strip=False,
    upx=True,
    console=True
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='piston'
)

# vim: ts=4 sw=4 expandtab ft=python
