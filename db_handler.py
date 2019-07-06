import sqlite3
import uuid
from _datetime import datetime
from pathlib import Path


class DbHandler:
    def __init__(self):
        self.conn = sqlite3.connect(str(Path.home()) + '/.local/share/FileWatcher/sync.db')
        self.cur = self.conn.cursor()
        self.cur.execute('''
            CREATE TABLE IF NOT EXISTS syncs (
            id TEXT PRIMARY KEY,
            time TEXT,
            path_to TEXT,
            filename TEXT,
            is_dir INTEGER,
            action TEXT,
            server TEXT,
            retries INTEGER,
            cookie INTEGER)
        ''')
        self.conn.commit()

    def save(self, db_row) -> list:
        # self.cur.execute('SELECT * FROM syncs WHERE path_to = ? AND filename = ?', (db_row[0], db_row[1]))
        # rows = self.cur.fetchall()
        # ids = []
        # if len(rows):
        #     for r in rows:
        #         ids.append(r[0])
        #     return ids
        _id = uuid.uuid4().hex
        self.cur.execute('INSERT INTO syncs VALUES (?,?,?,?,?,?,?,?,?)', (_id, datetime.now(), *db_row))
        self.conn.commit()
        return [_id]

    def get_by_cookie(self, cookie):
        self.cur.execute('SELECT * FROM syncs WHERE cookie = ?', (cookie,))
        return self.cur.fetchall()

    def delete(self, ids: list):
        if len(ids):
            for i in range(len(ids)):
                ids[i] = "'" + ids[i] + "'"
            cmd = 'DELETE FROM syncs WHERE id IN ({})'.format(','.join(ids))
            self.cur.execute(cmd)
            self.conn.commit()

    def close(self):
        self.conn.close()
