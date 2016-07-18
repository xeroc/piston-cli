from steembase import PrivateKey
from graphenebase import bip38
import os
import json
from appdirs import user_data_dir
import logging
from .storage import keyStorage, createTables
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
    password = None
    keysDb = None

    def __init__(self, rpc, *args, **kwargs):
        self.rpc = rpc

        if createTables:
            # migrate to new SQL based storage
            if self.exists():
                log.critical("Migrating old wallet format to new format!")
                self.migrateFromJSON()

    def unlock(self):
        if self.password is None:
            self.password = self.getPasswordConfirmed()

    def lock(self):
        self.password = None

    def migrateFromJSON(self):
        # Open Legacy Wallet and populate self.keys
        self.ensureOpen()
        print("Please provide a password for the new wallet")
        self.unlock()
        numKeys = len(self.keys)
        for i, key in enumerate(self.keys):
            self.addPrivateKey(key)
            log.critical("Migrated key %d of %d" % (i + 1, numKeys))
        log.critical("Migration completed")

    def encrypt_wif(self, wif):
        self.unlock()
        if self.password == "":
            return wif
        else:
            return format(bip38.encrypt(PrivateKey(wif), self.password), "encwif")

    def decrypt_wif(self, encwif):
        self.unlock()
        if self.password == "":
            return encwif
        else:
            return format(bip38.decrypt(encwif, self.password), "wif")

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
        keyStorage.add(self.encrypt_wif(wif), pub)

    def getPrivateKeyForPublicKey(self, pub):
        return self.decrypt_wif(keyStorage.getPrivateKeyForPublicKey(pub))

    def removePrivateKeyFromPublicKey(self, pub):
        keyStorage.delete(pub)

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
        return self.rpc.get_key_references([pub])[0][0]

    def getAccountFromPublicKey(self, pub):
        return self.rpc.get_key_references([pub])[0][0]

    def getAccount(self, pub):
        name = self.rpc.get_key_references([pub])[0]
        if not name:
            return ["n/a", "n/a", pub]
        else:
            account = self.rpc.get_account(name[0])
            keyType = self.getKeyType(account, pub)
            return [name[0], keyType, pub]

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

    def getPublicKeys(self):
        return keyStorage.getPublicKeys()
