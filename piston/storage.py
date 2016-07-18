import argparse
import sqlite3
import shutil
import time
import os
import sqlite3
from appdirs import user_data_dir
import logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.StreamHandler())

appname = "piston"
appauthor = "Fabian Schuh"


def sqlite3_backup(dbfile, backupdir):
    """Create timestamped database copy"""
    if not os.path.isdir(backupdir):
        os.mkdir(backupdir)
    backup_file = os.path.join(
        backupdir, 
        os.path.basename(storageDatabase) +
        time.strftime("-%Y%m%d-%H%M%S"))
    # Lock database before making a backup
    session.execute('begin immediate')
    # Make new backup file
    shutil.copyfile(dbfile, backup_file)
    log.info("Creating {}...".format(backup_file))
    # Unlock database
    engine.rollback()
    configStorage["lastBackup"] = time.time()


def clean_data(backup_dir):
    """Delete files older than NO_OF_DAYS days"""
    log.info("Cleaning up old backups")
    for filename in os.listdir(backup_dir):
        backup_file = os.path.join(backup_dir, filename)
        if os.stat(backup_file).st_ctime < (time.time() - 70 * 86400):
            if os.path.isfile(backup_file):
                os.remove(backup_file)
                log.info("Deleting {}...".format(ibackup_file))


class Key():
    __tablename__ = 'keys'

    def __init__(self):
        pass

    def exists_table(self):
        query = ("SELECT name FROM sqlite_master "
                 "WHERE type='table' AND name='%s'" % self.__tablename__)
        session.execute(query)
        return True if session.fetchone() else False

    def create_table(self):
        query = ('CREATE TABLE %s (' % self.__tablename__ +
                 'id INTEGER PRIMARY KEY AUTOINCREMENT,' +
                 'pub STRING(256),' +
                 'wif STRING(256)' +
                 ')')
        session.execute(query)
        engine.commit()

    def getPublicKeys(self):
        query = ("SELECT pub from %s " % (self.__tablename__))
        session.execute(query)
        results = session.fetchall()
        return [x[0] for x in results]

    def getPrivateKeyForPublicKey(self, pub):
        query = ("SELECT wif from %s " % (self.__tablename__) +
                 "WHERE pub='%s'" % pub)
        session.execute(query)
        key = session.fetchone()
        if key:
            return key[0]
        else:
            return None

    def add(self, wif, pub):
        if self.getPrivateKeyForPublicKey(pub):
            raise ValueError("Key already in storage")
        query = ('INSERT INTO %s (pub, wif) ' % self.__tablename__ +
                 'VALUES ("%s", "%s")' % (pub, wif))
        session.execute(query)
        engine.commit()

    def delete(self, pub):
        query = ("DELETE FROM %s " % (self.__tablename__) +
                 "WHERE pub='%s'" % pub)
        session.execute(query)
        engine.commit()


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
        session.execute(query)
        return True if session.fetchone() else False

    def create_table(self):
        query = ('CREATE TABLE %s (' % self.__tablename__ +
                 'id INTEGER PRIMARY KEY AUTOINCREMENT,' +
                 'key STRING(256),' +
                 'value STRING(256)' +
                 ')')
        session.execute(query)
        engine.commit()

    def __getitem__(self, key):
        """ This method behaves differently from regular `dict` in that
            it returns `None` if a key is not found!
        """
        query = ("SELECT value FROM %s " % (self.__tablename__) +
                 "WHERE key='%s'" % key
                 )
        session.execute(query)
        result = session.fetchone()
        if result:
            return result[0]
        else:
            if key in self.defaults:
                return self.defaults[key]
            else:
                return None

    def __contains__(self, key):
        if self[key]:
            return True
        else:
            return False

    def __setitem__(self, key, value):
        if self[key]:
            query = ("UPDATE %s " % (self.__tablename__) +
                     "SET value='%s' " % value +
                     "WHERE key='%s'" % key
                     )
        else:
            query = ("INSERT INTO %s (key, value) VALUES" % (self.__tablename__) +
                     "('%s', '%s')" % (key, value))
        session.execute(query)
        engine.commit()

    def __delitem__(self, key):
        query = ("DELETE FROM %s " % (self.__tablename__) +
                 "WHERE key='%s'" % key)
        session.execute(query)
        engine.commit()

    def __iter__(self):
        query = ("SELECT key, value from %s " % (self.__tablename__))
        session.execute(query)
        r = {}
        for key, value in session.fetchall():
            r[key] = value
        return iter(r)

    def __len__(self):
        query = ("SELECT id from %s " % (self.__tablename__))
        session.execute(query)
        return len(session.fetchall())


#: Storage
storageDatabase = "piston.sqlite"
data_dir = user_data_dir(appname, appauthor)
sqlDataBaseFile = os.path.join(data_dir, storageDatabase)

# Connect to Storage via SQLite3
engine = sqlite3.connect(sqlDataBaseFile)
session = engine.cursor()

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
if (not configStorage["lastBackup"] or 
        (time.time() - configStorage["lastBackup"]) > 60 * 60 * 7):
    backupdir = os.path.join(data_dir, "backups")
    sqlite3_backup(sqlDataBaseFile, backupdir)
    clean_data(data_dir)
