"""Durable operation receipts, never automatic deletion/resume authority."""
import json
import os
import sqlite3

from .move_fs import Location, MoveError, identity


class Journal:
    def __init__(self, path, source, destination, plan, index):
        parent = Location(os.path.dirname(path))
        fd = parent.open()
        self.db = None
        self.fd = None
        try:
            # mkdir is exclusive: never reuse an old/late-created operation directory.
            os.mkdir(os.path.basename(path), 0o700, dir_fd=fd)
            os.fsync(fd)
            self.fd = Location(path).open()
            self.db = sqlite3.connect(f'/proc/self/fd/{self.fd}/journal.sqlite')
            self.db.executescript('''
                PRAGMA synchronous=FULL;
                CREATE TABLE roots(kind TEXT,dev TEXT,ino TEXT);
                CREATE TABLE items(path TEXT PRIMARY KEY,keeper TEXT,size INTEGER,
                    metadata TEXT,state TEXT,stage TEXT,dev TEXT,ino TEXT,error TEXT,
                    source_signature TEXT,keeper_signature TEXT,sha256 TEXT);
            ''')
            for kind, rootfd in [('source', source), ('destination', destination)]:
                self.db.execute('INSERT INTO roots VALUES (?,?,?)', (kind, *map(str, identity(rootfd))))
            for path, keeper, size, meta in plan:
                def signature_for(relative):
                    return index.execute('SELECT dev,ino,size,mtime,ctime,digest FROM files WHERE path=?', (relative,)).fetchone()
                victim, kept = signature_for(path), signature_for(keeper)
                self.db.execute('INSERT INTO items(path,keeper,size,metadata,state,source_signature,keeper_signature,sha256) VALUES (?,?,?,?,?,?,?,?)',
                                (path, keeper, size, meta, 'planned', json.dumps(victim[:5]), json.dumps(kept[:5]), victim[5]))
            self.db.commit()
            os.fsync(self.fd)
        except BaseException:
            self.close()
            raise
        finally:
            os.close(fd)

    def state(self, path, state, stage=None, info=None, error=None):
        dev, ino = (None, None) if info is None else map(str, info)
        self.db.execute('UPDATE items SET state=?,stage=?,dev=?,ino=?,error=? WHERE path=?',
                        (state, stage, dev, ino, error, path))
        self.db.commit()
        os.fsync(self.fd)

    def error(self, path, code):
        self.db.execute('UPDATE items SET error=? WHERE path=?', (code, path))
        self.db.commit()
        os.fsync(self.fd)

    def close(self):
        if self.db is not None:
            self.db.close()
            self.db = None
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
