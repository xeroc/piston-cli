import argparse
import shutil
import time
import os
import sqlite3
from appdirs import user_data_dir
from datetime import datetime
import logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.StreamHandler())

appname = "piston"
appauthor = "Fabian Schuh"
storageDatabase = "piston.sqlite"
timeformat = "%Y%m%d-%H%M%S"


class Key():
    __tablename__ = 'keys'

    def __init__(self):
        pass

    def exists_table(self):
        query = ("SELECT name FROM sqlite_master "
                 "WHERE type='table' AND name='%s'" % self.__tablename__)
        connection = sqlite3.connect(sqlDataBaseFile)
        cursor = connection.cursor()
        cursor.execute(query)
        return True if cursor.fetchone() else False

    def create_table(self):
        query = ('CREATE TABLE %s (' % self.__tablename__ +
                 'id INTEGER PRIMARY KEY AUTOINCREMENT,' +
                 'pub STRING(256),' +
                 'wif STRING(256)' +
                 ')')
        connection = sqlite3.connect(sqlDataBaseFile)
        cursor = connection.cursor()
        cursor.execute(query)
        connection.commit()

    def getPublicKeys(self):
        query = ("SELECT pub from %s " % (self.__tablename__))
        connection = sqlite3.connect(sqlDataBaseFile)
        cursor = connection.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        return [x[0] for x in results]

    def getPrivateKeyForPublicKey(self, pub):
        query = ("SELECT wif from %s " % (self.__tablename__) +
                 "WHERE pub='%s'" % pub)
        connection = sqlite3.connect(sqlDataBaseFile)
        cursor = connection.cursor()
        cursor.execute(query)
        key = cursor.fetchone()
        if key:
            return key[0]
        else:
            return None

    def add(self, wif, pub):
        if self.getPrivateKeyForPublicKey(pub):
            raise ValueError("Key already in storage")
        query = ('INSERT INTO %s (pub, wif) ' % self.__tablename__ +
                 'VALUES ("%s", "%s")' % (pub, wif))
        connection = sqlite3.connect(sqlDataBaseFile)
        cursor = connection.cursor()
        cursor.execute(query)
        connection.commit()

    def delete(self, pub):
        query = ("DELETE FROM %s " % (self.__tablename__) +
                 "WHERE pub='%s'" % pub)
        connection = sqlite3.connect(sqlDataBaseFile)
        cursor = connection.cursor()
        cursor.execute(query)
        connection.commit()


class Configuration():
    __tablename__ = "config"
    defaults = {
        "categories_sorting": "trending",
        "default_vote_weight": 100.0,
        # "default_author": "xeroc",
        # "default_voter": "xeroc",
        "format": "markdown",
        "limit": 10,
        "list_sorting": "hot",
        "node": "wss://this.piston.rocks",
        "post_category": "steem",
        "rpcpassword": "",
        "rpcuser": "",
    }

    def exists_table(self):
        query = ("SELECT name FROM sqlite_master "
                 "WHERE type='table' AND name='%s'" % self.__tablename__)
        connection = sqlite3.connect(sqlDataBaseFile)
        cursor = connection.cursor()
        cursor.execute(query)
        return True if cursor.fetchone() else False

    def create_table(self):
        query = ('CREATE TABLE %s (' % self.__tablename__ +
                 'id INTEGER PRIMARY KEY AUTOINCREMENT,' +
                 'key STRING(256),' +
                 'value STRING(256)' +
                 ')')
        connection = sqlite3.connect(sqlDataBaseFile)
        cursor = connection.cursor()
        cursor.execute(query)
        connection.commit()

    def _haveKey(self, key):
        query = ("SELECT value FROM %s " % (self.__tablename__) +
                 "WHERE key='%s'" % key
                 )
        connection = sqlite3.connect(sqlDataBaseFile)
        cursor = connection.cursor()
        cursor.execute(query)
        return True if cursor.fetchone() else False

    def __getitem__(self, key):
        """ This method behaves differently from regular `dict` in that
            it returns `None` if a key is not found!
        """
        query = ("SELECT value FROM %s " % (self.__tablename__) +
                 "WHERE key='%s'" % key
                 )
        connection = sqlite3.connect(sqlDataBaseFile)
        cursor = connection.cursor()
        cursor.execute(query)
        result = cursor.fetchone()
        if result:
            return result[0]
        else:
            if key in self.defaults:
                return self.defaults[key]
            else:
                return None

    def __contains__(self, key):
        if self._haveKey(key):
            return True
        else:
            return False

    def __setitem__(self, key, value):
        if key in self:
            query = ("UPDATE %s " % (self.__tablename__) +
                     "SET value='%s' " % value +
                     "WHERE key='%s'" % key
                     )
        else:
            query = ("INSERT INTO %s (key, value) VALUES" % (self.__tablename__) +
                     "('%s', '%s')" % (key, value))
        connection = sqlite3.connect(sqlDataBaseFile)
        cursor = connection.cursor()
        cursor.execute(query)
        connection.commit()

    def __delitem__(self, key):
        query = ("DELETE FROM %s " % (self.__tablename__) +
                 "WHERE key='%s'" % key)
        connection = sqlite3.connect(sqlDataBaseFile)
        cursor = connection.cursor()
        cursor.execute(query)
        connection.commit()

    def __iter__(self):
        query = ("SELECT key, value from %s " % (self.__tablename__))
        connection = sqlite3.connect(sqlDataBaseFile)
        cursor = connection.cursor()
        cursor.execute(query)
        r = {}
        for key, value in cursor.fetchall():
            r[key] = value
        return iter(r)

    def __len__(self):
        query = ("SELECT id from %s " % (self.__tablename__))
        connection = sqlite3.connect(sqlDataBaseFile)
        cursor = connection.cursor()
        cursor.execute(query)
        return len(cursor.fetchall())


def sqlite3_backup(dbfile, backupdir):
    """Create timestamped database copy"""
    if not os.path.isdir(backupdir):
        os.mkdir(backupdir)
    backup_file = os.path.join(
        backupdir,
        os.path.basename(storageDatabase) +
        datetime.now().strftime("-" + timeformat))
    connection = sqlite3.connect(sqlDataBaseFile)
    cursor = connection.cursor()
    # Lock database before making a backup
    cursor.execute('begin immediate')
    # Make new backup file
    shutil.copyfile(dbfile, backup_file)
    log.info("Creating {}...".format(backup_file))
    # Unlock database
    connection.rollback()
    configStorage["foobar"] = datetime.now().strftime(timeformat)
    configStorage["lastBackup"] = datetime.now().strftime(timeformat)


def clean_data(backup_dir):
    """Delete files older than NO_OF_DAYS days"""
    log.info("Cleaning up old backups")
    for filename in os.listdir(backup_dir):
        backup_file = os.path.join(backup_dir, filename)
        if os.stat(backup_file).st_ctime < (time.time() - 70 * 86400):
            if os.path.isfile(backup_file):
                os.remove(backup_file)
                log.info("Deleting {}...".format(backup_file))


def refreshBackup():
    backupdir = os.path.join(data_dir, "backups")
    sqlite3_backup(sqlDataBaseFile, backupdir)
    clean_data(data_dir)

#: Storage
data_dir = user_data_dir(appname, appauthor)
sqlDataBaseFile = os.path.join(data_dir, storageDatabase)

# Create keyStorage
keyStorage = Key()
configStorage = Configuration()

# Create Tables if database is brand new
createTables = False
if not configStorage.exists_table():
    configStorage.create_table()
if not keyStorage.exists_table():
    createTables = True
    keyStorage.create_table()


# Backup the SQL database every 7 days
if ("lastBackup" not in configStorage or
        configStorage["lastBackup"] == ""):
    refreshBackup()

try:
    if (
        datetime.now() -
        datetime.strptime(configStorage["lastBackup"],
                          timeformat)
    ).days > 7:
        refreshBackup()
except:
    refreshBackup()
