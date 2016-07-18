from sqlalchemy.orm import load_only
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from .wallet_sql import session, createTables, engine

Base = declarative_base()


class Key(Base):
    __tablename__ = 'keys'

    id  = Column(Integer, primary_key=True)
    pub = Column(String)
    wif = Column(String)

    def __init__(self, wif, pub):
        self.wif = wif
        self.pub = pub
        session.add(self)
        session.commit()

    @staticmethod
    def getPublicKeys():
        pubs = session.query(Key).options(load_only("pub"))
        return [x.pub for x in pubs]

    @staticmethod
    def getPrivateKeyForPublicKey(pub):
        key = session.query(Key).filter_by(pub=pub).first()
        if key:
            return key.wif
        else:
            return None
