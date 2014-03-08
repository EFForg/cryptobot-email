#!/usr/bin/env python

# $ createdb dbname

from passlib.hash import sha256_crypt

from sqlalchemy import MetaData, Table, Column, String, ForeignKey, create_engine
from sqlalchemy.orm import mapper, relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
session = None

class BlockedEmail(Base):
  __tablename__ = 'unsubscribe'
  address = Column(String, primary_key=True)

  def __init__(self, address):
    self.address = address;


def createDB(engine):
    Base.metadata.create_all(engine)

def block_email(address):
    hashed_address = sha256_crypt.encrypt(address, rounds=12345, salt='aconstantsalt')
    if not session.query(BlockedEmail).filter_by(address=hashed_address).first():
      block = BlockedEmail(hashed_address)
      session.add(block)
      session.commit()

if __name__ == "__main__":
    engine = create_engine('postgresql://lilia:password@localhost/test', echo=True)
    createDB(engine)
    session = sessionmaker(engine)()

    block_email("foo@bar.com")

    print session.query(BlockedEmail).all()
