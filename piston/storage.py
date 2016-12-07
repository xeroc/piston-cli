import warnings
from steem.storage import DataDir as DataDirSteem
from steem.storage import Key as KeySteem
from steem.storage import Configuration as ConfigurationSteem
from steem.storage import MasterPassword as MasterPasswordSteem


class DataDir(DataDirSteem):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "[DeprecationWarning] Please replace 'import piston.storage' by 'import steem.storage'"
        )
        super(DataDir, self).__init__(*args, **kwargs)


class Key(KeySteem):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "[DeprecationWarning] Please replace 'import piston.storage' by 'import steem.storage'"
        )
        super(Key, self).__init__(*args, **kwargs)


class Configuration(ConfigurationSteem):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "[DeprecationWarning] Please replace 'import piston.storage' by 'import steem.storage'"
        )
        super(Configuration, self).__init__(*args, **kwargs)


class MasterPassword(MasterPasswordSteem):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "[DeprecationWarning] Please replace 'import piston.storage' by 'import steem.storage'"
        )
        super(MasterPassword, self).__init__(*args, **kwargs)


# Create keyStorage
keyStorage = Key()
configStorage = Configuration()

# Create Tables if database is brand new
if not configStorage.exists_table():
    configStorage.create_table()

newKeyStorage = False
if not keyStorage.exists_table():
    newKeyStorage = True
    keyStorage.create_table()
