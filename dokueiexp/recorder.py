import json

import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Boolean, String, DateTime, Integer
from sqlalchemy.dialects.mysql import TIMESTAMP as Timestamp
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects import sqlite

import datetime
import pandas as pd

from sqlalchemy.sql.functions import current_timestamp

Base = declarative_base()


def record_data2obj(data):
    return json.loads(data.decode('utf8'))


class RecordDB():
    def __init__(self, filename, echo=False):
        self.engine = sqlalchemy.create_engine(filename, echo=echo)
        Base.metadata.create_all(bind=self.engine)
        self.session = sessionmaker(bind=self.engine)()

    def new_session(self):
        return Session(self.engine)

    class Record(Base):
        __tablename__ = "records"
        username = Column(String(length=64), primary_key=True)
        case_id = Column(String(length=64), primary_key=True)
        data = Column(String(length=1024))
        elapsed_time = Column(Integer())
        last_update = Column(DateTime())
        ai = Column(Boolean(), primary_key=True)
        completed = Column(Boolean())

        def __init__(self, username: str, case_id: str, data: str,
                     elapsed_time: int, ai: bool, completed: bool):
            self.username = username
            self.case_id = case_id
            self.data = data
            self.ai = ai
            self.completed = completed
            self.elapsed_time = elapsed_time
            self.last_update = datetime.datetime.now()

        def to_dict(self):
            data = record_data2obj(self.data)
            return dict(username=self.username,
                        case_id=self.case_id,
                        ai=self.ai,
                        last_update=self.last_update,
                        elapsed_time=self.elapsed_time,
                        data=json.dumps(data),
                        completed=self.completed)

    def get_record(self, username, case_id, ai, sess=None):
        if sess is None:
            sess = self.session
        return sess.query(self.Record).get((username, case_id, ai))

    def update_record(self,
                      username: str,
                      case_id: str,
                      data: bytes,
                      elapsed_time: int,
                      ai: bool,
                      completed: bool,
                      sess=None):
        if sess is None:
            sess = self.session
        record = self.Record(username, case_id, data, elapsed_time, ai,
                             completed)
        match = sess.query(self.Record).get(
            (record.username, record.case_id, record.ai))
        if match:
            match.last_update = datetime.datetime.now()
            match.data = record.data
            match.elapsed_time = elapsed_time
            match.completed = record.completed
            sess.commit()
        else:
            sess.add(instance=record)
            sess.commit()

    def to_csv(self, filename, sess=None):
        if sess is None:
            sess = self.session
        rows = []
        for r in sess.query(self.Record):
            rows.append(r.to_dict())

        df = pd.DataFrame(rows)
        df.to_csv(filename, index=False, encoding='cp932')
