from steembase import PrivateKey
from graphenebase import bip38
import os
import json
from appdirs import user_data_dir
import logging
from .wallet_legacy import LegacyWallet

log = logging.getLogger(__name__)
appname = "piston"
appauthor = "Fabian Schuh"
prefix = "STM"
# prefix = "TST"


class InvalidWifError(Exception):
    pass


class Wallet(LegacyWallet):
    keys = []
    rpc = None
    masterpassword = None

    # Keys from database
    configStorage = None
    MasterPassword = None
    keyStorage = None

    # Manually provided keys
    keys = {}  # struct with pubkey as key and wif as value

    def __init__(self, rpc, *args, **kwargs):
        self.rpc = rpc

        if "wif" not in kwargs:
            """ If no keys are provided manually we load the SQLite
                keyStorage
            """
            from .storage import (keyStorage,
                                  newKeyStorage,
                                  MasterPassword,
                                  configStorage)
            self.configStorage = configStorage
            self.MasterPassword = MasterPassword
            self.keyStorage = keyStorage
            if newKeyStorage:
                # migrate to new SQL based storage
                if self.exists():
                    log.critical("Migrating old wallet format to new format!")
                    self.migrateFromJSON()
            if not self.created():
                self.newWallet()
        else:
            self.setKeys(kwargs["wif"])

    def setKeys(self, wifs):
        """ This method is strictly only for in memory keys that are
            passed to Wallet/Steem with the ``keys`` argument
        """
        print("setting keys")
        if not isinstance(wifs, list):
            wifs = [wifs]
        for wif in wifs:
            try:
                key = PrivateKey(wif)
            except:
                raise InvalidWifError
            self.keys[format(key.pubkey, "STM")] = str(key)

    def unlock(self, pwd=None):
        if (self.masterpassword is None and
                self.configStorage[self.MasterPassword.config_key]):
            if pwd is None:
                pwd = self.getPassword()
            if pwd == "":
                self.masterpassword = pwd
                return
            else:
                masterpwd = self.MasterPassword(pwd)
                self.masterpassword = masterpwd.decrypted_master

    def lock(self):
        self.masterpassword = None

    def locked(self):
        return False if self.masterpassword else True

    def changePassphrase(self):
        # Open Existing Wallet
        currentpwd = self.getPassword()
        if currentpwd != "":
            masterpwd = self.MasterPassword(currentpwd)
            self.masterpassword = masterpwd.decrypted_master
        else:
            self.masterpassword = ""
        print("Please provide the new password")
        newpwd = self.getPasswordConfirmed()
        if newpwd:
            if currentpwd == "":
                masterpwd = self.MasterPassword(newpwd)
                self.reencryptKeys(currentpwd, masterpwd.decrypted_master)
            else:
                # only change the masterpassword
                masterpwd.changePassword(newpwd)
        else:
            self.reencryptKeys(currentpwd, newpwd)
            masterpwd.purge()

    def reencryptKeys(self, oldpassword, newpassword):
        # remove encryption from database
        allPubs = self.getPublicKeys()
        for i, pub in enumerate(allPubs):
            log.critical("Updating key %d of %d" % (i + 1, len(allPubs)))
            self.masterpassword = oldpassword
            wif = self.getPrivateKeyForPublicKey(pub)
            self.masterpassword = newpassword
            if self.keyStorage:
                self.keyStorage.updateWif(pub, wif)
        log.critical("Removing password complete")

    def created(self):
        if len(self.getPublicKeys()):
            # Already keys installed
            return True
        elif self.MasterPassword.config_key in self.configStorage:
            # no keys but a master password
            return True
        else:
            return False

    def newWallet(self):
        if self.created():
            raise Exception("You already have created a wallet!")
        print("Please provide a password for the new wallet")
        pwd = self.getPasswordConfirmed()
        masterpwd = self.MasterPassword(pwd)
        self.masterpassword = masterpwd.decrypted_master

    def migrateFromJSON(self):
        # Open Legacy Wallet and populate self.keys
        self.ensureOpen()
        self.newWallet()
        numKeys = len(self.keys)
        for i, key in enumerate(self.keys):
            self.addPrivateKey(key)
            log.critical("Migrated key %d of %d" % (i + 1, numKeys))
        log.critical("Migration completed")

    def encrypt_wif(self, wif):
        self.unlock()
        if self.masterpassword == "":
            return wif
        else:
            return format(bip38.encrypt(PrivateKey(wif), self.masterpassword), "encwif")

    def decrypt_wif(self, encwif):
        try:
            # Try to decode as wif
            PrivateKey(encwif)
            return encwif
        except:
            pass
        self.unlock()
        return format(bip38.decrypt(encwif, self.masterpassword), "wif")

    def getPassword(self):
        import getpass
        return getpass.getpass('Passphrase: ')

    def getPasswordConfirmed(self):
        import getpass
        while True :
            pw = getpass.getpass('Passphrase: ')
            if not pw:
                print("You have chosen an empty password! " +
                      "We assume you understand the risks!")
                return ""
                break
            else:
                pwck = getpass.getpass('Retype passphrase: ')
                if (pw == pwck) :
                    return(pw)
                else :
                    print("Given Passphrases do not match!")

    def addPrivateKey(self, wif):
        try:
            pub = format(PrivateKey(wif).pubkey, prefix)
        except:
            raise InvalidWifError("Invalid Private Key Format. Please use WIF!")
        if self.keyStorage:
            self.keyStorage.add(self.encrypt_wif(wif), pub)

    def getPrivateKeyForPublicKey(self, pub):
        if self.keyStorage:
            return self.decrypt_wif(self.keyStorage.getPrivateKeyForPublicKey(pub))
        else:
            if pub in self.keys:
                return self.keys[pub]

    def removePrivateKeyFromPublicKey(self, pub):
        if self.keyStorage:
            self.keyStorage.delete(pub)

    def removeAccount(self, account):
        accounts = self.getAccounts()
        for a in accounts:
            if a["name"] == account:
                self.removePrivateKeyFromPublicKey(a["pubkey"])

    def getOwnerKeyForAccount(self, name):
        account = self.rpc.get_account(name)
        for authority in account["owner"]["key_auths"]:
            key = self.getPrivateKeyForPublicKey(authority[0])
            if key:
                return key
        return False

    def getPostingKeyForAccount(self, name):
        account = self.rpc.get_account(name)
        for authority in account["posting"]["key_auths"]:
            key = self.getPrivateKeyForPublicKey(authority[0])
            if key:
                return key
        return False

    def getMemoKeyForAccount(self, name):
        account = self.rpc.get_account(name)
        key = self.getPrivateKeyForPublicKey(account["memo_key"])
        if key:
            return key
        return False

    def getActiveKeyForAccount(self, name):
        account = self.rpc.get_account(name)
        for authority in account["active"]["key_auths"]:
            key = self.getPrivateKeyForPublicKey(authority[0])
            if key:
                return key
        return False

    def getAccountFromPrivateKey(self, wif):
        pub = format(PrivateKey(wif).pubkey, prefix)
        return self.getAccountFromPublicKey(pub)

    def getAccountFromPublicKey(self, pub):
        names = self.rpc.get_key_references([pub])[0]
        if not names:
            return None
        else:
            return names[0]

    def getAccount(self, pub):
        name = self.getAccountFromPublicKey(pub)
        if not name:
            return {"name": None,
                    "type": None,
                    "pubkey": pub
                    }
        else:
            account = self.rpc.get_account(name)
            keyType = self.getKeyType(account, pub)
            return {"name": name,
                    "type": keyType,
                    "pubkey": pub
                    }

    def getKeyType(self, account, pub):
        if pub == account["memo_key"]:
            return "memo"
        for authority in ["owner", "posting", "active"]:
            for key in account[authority]["key_auths"]:
                if pub == key[0]:
                    return authority
        return None

    def getAccounts(self):
        return [self.getAccount(a) for a in self.getPublicKeys()]

    def getAccountsWithPermissions(self):
        accounts = [self.getAccount(a) for a in self.getPublicKeys()]
        r = {}
        for account in accounts:
            name = account["name"]
            if not name:
                continue
            type = account["type"]
            if name not in r:
                r[name] = {"posting": False,
                           "owner": False,
                           "active": False,
                           "memo": False}
            r[name][type] = True
        return r

    def getPublicKeys(self):
        if self.keyStorage:
            return self.keyStorage.getPublicKeys()
        else:
            return list(self.keys.keys())
