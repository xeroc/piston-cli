import os
import json
import collections
from appdirs import user_data_dir
import logging
log = logging.getLogger("piston.configuration")
appname = "piston"
appauthor = "Fabian Schuh"
configFile = "config.json"


class Configuration(collections.MutableMapping):

    def __init__(self, *args, **kwargs):
        self.store = dict()
        self.update(dict(*args, **kwargs))  # use the free update to set keys
        self._loadConfig()

    def __getitem__(self, key):
        """ This method behaves differently from regular `dict` in that
            it returns `None` if a key is not found!
        """
        internalKey = self.__keytransform__(key)
        if internalKey in self.store:
            return self.store[internalKey]
        else:
            return None

    def __setitem__(self, key, value):
        self.store[self.__keytransform__(key)] = value
        self._storeConfig()

    def __delitem__(self, key):
        del self.store[self.__keytransform__(key)]
        self._storeConfig()

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)

    def __keytransform__(self, key):
        return key

    def mkdir_p(self, path):
        if os.path.isdir(path):
            return
        else:
            try:
                os.makedirs(path)
            except FileExistsError:
                return
            except OSError:
                raise

    def _storeConfig(self):
        data_dir = user_data_dir(appname, appauthor)
        f = os.path.join(data_dir, configFile)
        log.info("Your configuration file is located at " + f)
        self.mkdir_p(data_dir)
        with open(f, 'w') as fp:
            json.dump(self.store, fp)

    def _loadConfig(self):
        data_dir = user_data_dir(appname, appauthor)
        f = os.path.join(data_dir, configFile)
        if os.path.isfile(f) :
            with open(f, 'r') as fp:
                try:
                    self.update(json.load(fp))  # use the free update to set keys
                    return self
                except:
                    raise ValueError("Error loading configuration :(")
        else:
            return []
