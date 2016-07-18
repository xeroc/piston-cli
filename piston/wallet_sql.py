import os
from .wallet import (
    appname,
    appauthor,
    walletDatabase,
    user_data_dir
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

data_dir = user_data_dir(appname, appauthor)
sqlDataBaseFile = os.path.join(data_dir, walletDatabase)
createTables = False
if not os.path.isfile(sqlDataBaseFile):
    createTables = True

engine = create_engine('sqlite:///%s' % sqlDataBaseFile, echo=True)

Session = sessionmaker(bind=engine)
session = Session()
