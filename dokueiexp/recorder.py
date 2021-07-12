import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Boolean, String, DateTime
from sqlalchemy.dialects.mysql import TIMESTAMP as Timestamp
from sqlalchemy.orm import sessionmaker, Session
import datetime
import pandas as pd

from sqlalchemy.sql.functions import current_timestamp

Base = declarative_base()


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
        last_update = Column(DateTime(), default=datetime.datetime.utcnow())
        completed = Column(Boolean())

        def __init__(self, username: str, case_id: str, data: str,
                     completed: bool):
            self.username = username
            self.case_id = case_id
            self.data = data
            self.completed = completed

        def to_dict(self):
            return dict(username=self.username,
                        case_id=self.case_id,
                        data=self.data.decode('utf8'),
                        completed=self.completed)

    def get_record(self, username, case_id, sess=None):
        if sess is None:
            sess = self.session
        return sess.query(self.Record).get((username, case_id))

    def update_record(self, username, case_id, data, completed, sess=None):
        if sess is None:
            sess = self.session
        record = self.Record(username, case_id, data, completed)
        match = sess.query(self.Record).get((record.username, record.case_id))
        if match:
            match.last_update = datetime.datetime.utcnow()
            match.data = record.data
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
        df.to_csv(filename, index=False)
