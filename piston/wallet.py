from steembase.account import PrivateKey
from graphenebase import bip38
import os
import json
from appdirs import user_data_dir
import logging
from .wallet_legacy import LegacyWallet

log = logging.getLogger(__name__)
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
        """ The wallet is meant to maintain access to private keys for
            your accounts. It either uses manually provided private keys
            or uses a SQLite database managed by storage.py.

            :param SteemNodeRPC rpc: RPC connection to a Steem node
            :param array wif: Predefine the wif keys to shortcut the wallet database
        """
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
        log.debug("Force setting of private keys. Not using the wallet database!")
        if not isinstance(wifs, list):
            wifs = [wifs]
        for wif in wifs:
            try:
                key = PrivateKey(wif)
            except:
                raise InvalidWifError
            self.keys[format(key.pubkey, "STM")] = str(key)

    def unlock(self, pwd=None):
        """ Unlock the wallet database
        """
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
        """ Lock the wallet database
        """
        self.masterpassword = None

    def locked(self):
        """ Is the wallet database locked?
        """
        return False if self.masterpassword else True

    def changePassphrase(self):
        """ Change the passphrase for the wallet database
        """
        # Open Existing Wallet
        currentpwd = self.getPassword()
        if currentpwd != "":
            masterpwd = self.MasterPassword(currentpwd)
            self.masterpassword = masterpwd.decrypted_master
        else:
            self.masterpassword = ""
        print("Please provide the new password")
        newpwd = self.getPassword(confirm=True)
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
        """ Reencrypt keys in the wallet database
        """
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
        """ Do we have a wallet database already?
        """
        if len(self.getPublicKeys()):
            # Already keys installed
            return True
        elif self.MasterPassword.config_key in self.configStorage:
            # no keys but a master password
            return True
        else:
            return False

    def newWallet(self):
        """ Create a new wallet database
        """
        if self.created():
            raise Exception("You already have created a wallet!")
        print("Please provide a password for the new wallet")
        pwd = self.getPassword(confirm=True)
        masterpwd = self.MasterPassword(pwd)
        self.masterpassword = masterpwd.decrypted_master

    def migrateFromJSON(self):
        """ (Legacy) Migrate code from former wallet database
        """
        # Open Legacy Wallet and populate self.keys
        self.ensureOpen()
        self.newWallet()
        numKeys = len(self.keys)
        for i, key in enumerate(self.keys):
            self.addPrivateKey(key)
            log.critical("Migrated key %d of %d" % (i + 1, numKeys))
        log.critical("Migration completed")

    def encrypt_wif(self, wif):
        """ Encrypt a wif key
        """
        self.unlock()
        if self.masterpassword == "":
            return wif
        else:
            return format(bip38.encrypt(PrivateKey(wif), self.masterpassword), "encwif")

    def decrypt_wif(self, encwif):
        """ decrypt a wif key
        """
        try:
            # Try to decode as wif
            PrivateKey(encwif)
            return encwif
        except:
            pass
        self.unlock()
        return format(bip38.decrypt(encwif, self.masterpassword), "wif")

    def getPassword(self, confirm=False, text='Passphrase: '):
        """ Obtain a password from the user
        """
        import getpass
        if "UNLOCK" in os.environ:
            # overwrite password from environmental variable
            return os.environ.get("UNLOCK")
        if confirm:
            # Loop until both match
            while True :
                pw = self.getPassword(confirm=False)
                if not pw:
                    print("You have chosen an empty password! " +
                          "We assume you understand the risks!")
                    return ""
                else:
                    pwck = self.getPassword(
                        confirm=False,
                        text="Confirm Passphrase: "
                    )
                    if (pw == pwck) :
                        return(pw)
                    else :
                        print("Given Passphrases do not match!")
        else:
            # return just one password
            return getpass.getpass(text)

    def addPrivateKey(self, wif):
        """ Add a private key to the wallet database
        """
        if isinstance(wif, PrivateKey):
            wif = str(wif)
        try:
            pub = format(PrivateKey(wif).pubkey, prefix)
        except:
            raise InvalidWifError("Invalid Private Key Format. Please use WIF!")
        if self.keyStorage:
            self.keyStorage.add(self.encrypt_wif(wif), pub)

    def getPrivateKeyForPublicKey(self, pub):
        """ Obtain the private key for a given public key

            :param str pub: Public Key
        """
        if self.keyStorage:
            return self.decrypt_wif(self.keyStorage.getPrivateKeyForPublicKey(pub))
        else:
            if pub in self.keys:
                return self.keys[pub]
            elif len(self.keys) == 1:
                # If there is only one key in my overwrite-storage, then
                # use that one! Feather it will has sufficient
                # authorization is left to ensure by the developer
                return list(self.keys.values())[0]

    def removePrivateKeyFromPublicKey(self, pub):
        """ Remove a key from the wallet database
        """
        if self.keyStorage:
            self.keyStorage.delete(pub)

    def removeAccount(self, account):
        """ Remove all keys associated with a given account
        """
        accounts = self.getAccounts()
        for a in accounts:
            if a["name"] == account:
                self.removePrivateKeyFromPublicKey(a["pubkey"])

    def getOwnerKeyForAccount(self, name):
        """ Obtain owner Private Key for an account from the wallet database
        """
        account = self.rpc.get_account(name)
        for authority in account["owner"]["key_auths"]:
            key = self.getPrivateKeyForPublicKey(authority[0])
            if key:
                return key
        return False

    def getPostingKeyForAccount(self, name):
        """ Obtain owner Posting Key for an account from the wallet database
        """
        account = self.rpc.get_account(name)
        for authority in account["posting"]["key_auths"]:
            key = self.getPrivateKeyForPublicKey(authority[0])
            if key:
                return key
        return False

    def getMemoKeyForAccount(self, name):
        """ Obtain owner Memo Key for an account from the wallet database
        """
        account = self.rpc.get_account(name)
        key = self.getPrivateKeyForPublicKey(account["memo_key"])
        if key:
            return key
        return False

    def getActiveKeyForAccount(self, name):
        """ Obtain owner Active Key for an account from the wallet database
        """
        account = self.rpc.get_account(name)
        for authority in account["active"]["key_auths"]:
            key = self.getPrivateKeyForPublicKey(authority[0])
            if key:
                return key
        return False

    def getAccountFromPrivateKey(self, wif):
        """ Obtain account name from private key
        """
        pub = format(PrivateKey(wif).pubkey, prefix)
        return self.getAccountFromPublicKey(pub)

    def getAccountFromPublicKey(self, pub):
        """ Obtain account name from public key
        """
        # FIXME, this only returns the first associated key.
        # If the key is used by multiple accounts, this
        # will surely lead to undesired behavior
        names = self.rpc.get_key_references([pub])[0]
        if not names:
            return None
        else:
            return names[0]

    def getAccount(self, pub):
        """ Get the account data for a public key
        """
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
        """ Get key type
        """
        if pub == account["memo_key"]:
            return "memo"
        for authority in ["owner", "posting", "active"]:
            for key in account[authority]["key_auths"]:
                if pub == key[0]:
                    return authority
        return None

    def getAccounts(self):
        """ Return all accounts installed in the wallet database
        """
        return [self.getAccount(a) for a in self.getPublicKeys()]

    def getAccountsWithPermissions(self):
        """ Return a dictionary for all installed accounts with their
            corresponding installed permissions
        """
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
        """ Return all installed public keys
        """
        if self.keyStorage:
            return self.keyStorage.getPublicKeys()
        else:
            return list(self.keys.keys())
