#!/usr/bin/env python

from passlib.hash import sha1_crypt
from random import SystemRandom
from sqlalchemy import MetaData, Table, Column, String, ForeignKey, create_engine, Integer
from sqlalchemy.orm import mapper, relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
SQLAlchemyBase = declarative_base()

class BlockedEmail(SQLAlchemyBase):
  __tablename__ = 'unsubscribe'
  hashed_address = Column(String, primary_key=True)

  def __init__(self, hashed_address):
    self.hashed_address = hashed_address

class Hash(SQLAlchemyBase):
  __tablename__ = 'hash'
  uid = Column(Integer, primary_key=True)
  salt = Column(String)
  rounds = Column(Integer)
  name = Column(String) # just for reference

  def __init__(self, salt, rounds, name='SHA1'):
    self.salt = salt
    self.rounds = rounds
    self.name = name


class Database():
  def __init__(self, url, create=False):
    self.engine = create_engine(url, echo=True)

    if create:
      self.create()
      self.session = sessionmaker(self.engine)()
      self.create_hash_params() # requires self.session
    else:
      self.session = sessionmaker(engine)()

    self.hash_params = self.session.query(Hash).last()

  def create(self):
    SQLAlchemyBase.metadata.create_all(self.engine)


  def random_string(self):
    return ''.join(SystemRandom.choice(string.ascii_uppercase + string.digits) for x in range(32))

  def create_hash_params(self):
    salt = self.random_string()
    rounds = 12345
    hash_params = Hash(salt, rounds)
    self.session.add(hash_params)
    self.session.commit()

  def hash(self, email_address):
    # todo: 1. support for other hash algorithms based on hash_params.name
    #       2. hash using all the configs, iteratively. this way if the
    #          salt is ever compromised, just add a new salt on top.
    return sha1_crypt.encrypt(address, rounds=self.hash_params.rounds, salt=self.hash_params.salt)

  def find(self, email_address):
    self.session.query(BlockedEmail).filter_by(hashed_address=self.hash(email_address)).first()

  def add(self, email_address):
    block = BlockedEmail(self.hash(email_address))
    self.session.add(block)
    self.session.commit()


def block_email(address, db):
    if not db.find(address):
      db.add(address)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Cryptobot unsubscribe parser")
    parser.add_argument('--create', dest='createDB', action='store_true', default=False)
    parser.add_argument('--add', dest='email', action='store')

    db = Database(config.DATABASE_URL, createDB)

    if email:
      block_email(email)

    print db.session.query(BlockedEmail).all()
