import json

import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Boolean, String, DateTime, Integer
from sqlalchemy.orm import Session

import datetime
import pandas as pd

Base = declarative_base()


def record_data2obj(data):
    return json.loads(data.decode('utf8'))


class RecordDB():
    def __init__(self, filename, echo=False):
        self.engine = sqlalchemy.create_engine(filename, echo=echo)
        Base.metadata.create_all(bind=self.engine)

    def new_session(self) -> Session:
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

        def __init__(self, username: str, case_id: str, data,
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

    def get_record(self, username: str, case_id: str, ai: bool, sess: Session):
        return sess.query(self.Record).get((username, case_id, ai))

    def update_record(self,
                      username: str,
                      case_id: str,
                      data,
                      elapsed_time: int,
                      ai: bool,
                      completed: bool,
                      sess: Session):
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

    def to_csv(self, filename, sess: Session):
        rows = []
        for r in sess.query(self.Record):
            rows.append(r.to_dict())

        df = pd.DataFrame(rows)
        df.to_csv(filename, index=False, encoding='cp932')

    def from_csv(self, filename, sess: Session):
        df = pd.read_csv(filename, encoding='cp932')
        for _, row in df.iterrows():
            record = self.Record(row.get('username'), str(row.get('case_id')),
                                 row.get('data'), int(row.get('elapsed_time')),
                                 bool(row.get('ai')),
                                 bool(row.get('completed')))
            record.last_update = datetime.datetime.fromisoformat(
                row.get('last_update'))
            sess.add(instance=record)
        sess.commit()


def main():
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(
        description='Convert between sqlite3 database and csv file.')
    parser.add_argument('input',
                        help='Input sqlite3/csv filename:',
                        metavar='<input>')
    parser.add_argument('output',
                        help='Output sqlite3/csv filename',
                        metavar='<output>')

    args = parser.parse_args()

    in_filename = Path(args.input)
    out_filename = Path(args.output)

    if (in_filename.suffix == '.csv'
            and out_filename.suffix == '.sqlite3'):  # csv -> db
        if (out_filename.exists()):
            print(out_filename, ' already exists')
            return 1
        db = RecordDB('sqlite:///' + args.output.replace('\\', '/'))
        with db.new_session() as sess:
            db.from_csv(args.input, sess)

    elif (in_filename.suffix == '.sqlite3'
          and out_filename.suffix == '.csv'):  # db -> csv
        db = RecordDB('sqlite:///' + args.input.replace('\\', '/'))
        with db.new_session() as sess:
            db.to_csv(args.output, sess)
    else:
        print('Invalid input output combination')
        return 1
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
