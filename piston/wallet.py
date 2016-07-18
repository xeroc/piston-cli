from Crypto import Random
from Crypto.Cipher import AES
import hashlib
import base64
from steembase import PrivateKey
from graphenebase import bip38
import os
import json
from appdirs import user_data_dir
import logging
from .storage import keyStorage, createTables

log = logging.getLogger(__name__)
appname = "piston"
appauthor = "Fabian Schuh"

# legacy wallet
walletFile = "wallet.dat"

prefix = "STM"
# prefix = "TST"


class InvalidWifError(Exception):
    pass


class Wallet(object):
    keys = []
    rpc = None
    password = None
    keysDb = None

    # legacy aes encryption
    aes = None

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
        self.ensureOpen()
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

    #########################
    # Legacy Wallet Code
    #########################
    def open(self, password=None):
        if not password and not self.keys:
            # try to load the file without password
            import getpass
            if self.exists():
                if not self._openWallet(""):
                    print("Please unlock your existing wallet!")
                    while True :
                        pw = getpass.getpass('Passphrase: ')
                        if self._openWallet(pw):
                            break
            else:
                print("No wallet has been created yet. " +
                      "Please provide a passphrase for it!")
                while True :
                    pw = getpass.getpass('Passphrase: ')
                    if not pw:
                        print("You have chosen an empty password! " +
                              "We assume you understand the risks!")
                        self._openWallet(pw)
                        break
                    else:
                        pwck = getpass.getpass('Retype passphrase: ')
                        if (pw == pwck) :
                            self._openWallet(pw)
                            break
                        else :
                            print("Given Passphrases do not match!")

    def _openWallet(self, pw):
        if pw != "":
            self.aes = AESCipher(pw)

        if self.exists():
            try:
                self.keys = self._loadPrivateKeys()
                return True
            except:
                return False
        else:
            self._storeWallet()
            return True

    def isOpen(self):
        return self.keys

    def ensureOpen(self):
        if not self.isOpen():
            self.open()

    @staticmethod
    def exists():
        data_dir = user_data_dir(appname, appauthor)
        f = os.path.join(data_dir, walletFile)
        return os.path.isfile(f)

    def mkdir_p(self, path):
        if os.path.isdir(path):
            return
        else:
            try:
                os.makedirs(path)
            except OSError:
                raise

    def _storeWallet(self):
        data_dir = user_data_dir(appname, appauthor)
        f = os.path.join(data_dir, walletFile)
        log.info("Your encrypted wallet file is located at " + f)
        self.mkdir_p(data_dir)
        try:
            # Test if ciphertext can be constructed
            if self.aes:
                self.aes.encrypt(json.dumps(self.keys))
            else:
                json.dumps(self.keys)

            with open(f, 'w') as fp:
                if self.aes:
                    ciphertext = self.aes.encrypt(json.dumps(self.keys))
                    fp.write(ciphertext)
                else:
                    json.dump(self.keys, fp)
        except:
            raise Exception("Error formating wallet. Skipping ..")

    def _loadPrivateKeys(self):
        data_dir = user_data_dir(appname, appauthor)
        f = os.path.join(data_dir, walletFile)
        if os.path.isfile(f) :
            with open(f, 'r') as fp:
                try:
                    if self.aes:
                        ciphertext = fp.read()
                        plaintext = self.aes.decrypt(ciphertext)
                        self.keys = json.loads(plaintext)
                    else:
                        self.keys = json.load(fp)
                    return self.keys
                except:
                    raise ValueError("Error decrypting/loading keys! Check passphrase!")
        else:
            return []


class AESCipher(object):
    """
    A classical AES Cipher. Can use any size of data and any size of password thanks to padding.
    Also ensure the coherence and the type of the data with a unicode to byte converter.
    """
    def __init__(self, key):
        self.bs = 32
        self.key = hashlib.sha256(AESCipher.str_to_bytes(key)).digest()

    @staticmethod
    def str_to_bytes(data):
        u_type = type(b''.decode('utf8'))
        if isinstance(data, u_type):
            return data.encode('utf8')
        return data

    def _pad(self, s):
        return s + (self.bs - len(s) % self.bs) * AESCipher.str_to_bytes(chr(self.bs - len(s) % self.bs))

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s) - 1:])]

    def encrypt(self, raw):
        raw = self._pad(AESCipher.str_to_bytes(raw))
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw)).decode('utf-8')

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')
