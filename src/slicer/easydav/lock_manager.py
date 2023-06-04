# -*- coding: utf-8 -*-

'''Stores lock data in a SQLite database. SQLite handles the cross-process
and cross-thread synchronization, while this code handles WebDAV lock semantics.
'''

import os.path
import davutils
import sqlite3
from uuid import uuid4
import datetime
from davutils import DAVError

class Lock:
    '''Convenience wrapper for database rows returned from LockManager.'''
    def __init__(self, row):
        self.urn = str(row["urn"])
        self.path = unicode(row["path"])
        self.shared = row["shared"]
        self.owner = row["owner"]
        self.infinite_depth = row["infinite_depth"]
        self.valid_until = row["valid_until"]
    
    def __eq__(self, other):
        return isinstance(other, Lock) and other.urn == self.urn

    def __repr__(self):
        return '<Lock ' + self.urn + ' on ' + repr(self.path) + '>'

    def seconds_until_timeout(self):
        '''Return the number of seconds from current time to the moment when
        the lock expires.
        '''
        delta = self.valid_until - datetime.datetime.utcnow()
        return delta.seconds + delta.days * 86400

class LockManager:
    '''Implementation of WebDAV lock semantics.'''
    def __init__(self):
        # Lock_db can be absolute path or relative to root dir.
        dbpath = os.path.join(config.root_dir, config.lock_db)
        newfile = not os.path.exists(dbpath)
        
        self.db_conn = sqlite3.connect(dbpath,
            isolation_level = None,
            timeout = config.lock_wait,
            detect_types=sqlite3.PARSE_DECLTYPES)
        self.db_conn.row_factory = sqlite3.Row
        self.db_cursor = self.db_conn.cursor()
        
        if newfile:
            self._create_tables()
        else:
            self._purge_locks()
    
    def _create_tables(self):
        self._sql_query('''CREATE TABLE locks (
            urn TEXT PRIMARY KEY,
            path TEXT,
            shared BOOLEAN,
            owner TEXT,
            infinite_depth BOOLEAN,
            valid_until TIMESTAMP)''')
        
        self._sql_query('CREATE INDEX locks_idx1 ON locks (path)')
        self._sql_query('CREATE INDEX locks_idx2 ON locks (valid_until)')
    
    def _purge_locks(self):
        '''Remove all expired locks from the database.'''
        # To avoid unnecessary write lock on the database file,
        # first check if such records exist.
        self._sql_query('''SELECT 1 FROM locks WHERE
            valid_until < DATETIME('now') LIMIT 1''')
        
        if self.db_cursor.fetchone() is not None:
            self._sql_query('''DELETE FROM locks WHERE
                valid_until < DATETIME('now')''')
    
    def _sql_query(self, *args, **kwargs):
        '''Run a database query and wrap SQLite OperationalErrors, such
        as locked databases.
        '''
        try:
            self.db_cursor.execute(*args, **kwargs)
        except sqlite3.OperationalError, e:
            if 'locked' in e.message:
                raise DAVError('503 Service Unavailable: Lock DB is busy')
            else:
                raise DAVError('500 Internal Server Error: Lock DB: ' + e.message)

    def get_locks(self, rel_path, recursive):
        '''Returns all locks that apply to the resource defined by rel_path.
        This includes:
         - Locks on the resource itself
         - Locks on any parent collections
         - If recursive is True, locks on any resources inside the collection
        Result is a list of Lock objects.
        '''
        assert not rel_path.startswith('/')
        path_exprs = ['path = ?']
        path_args = [rel_path]
        
        # Construct a list of parent directories that have to be checked
        # for locks.
        partial_path = rel_path
        while partial_path:
            partial_path = os.path.dirname(partial_path)
            path_exprs.append('(infinite_depth AND path = ?)')
            path_args.append(partial_path)

        # Check for any resources inside this collection
        if recursive:
            if rel_path != '':
                prefix = rel_path + '/'
            else:
                prefix = ''
            
            path_exprs.append('SUBSTR(path,1,?) = ?')
            path_args.append(len(prefix))
            path_args.append(prefix)

        self._sql_query('SELECT * FROM locks WHERE '
            + ' OR '.join(path_exprs), path_args)
        return map(Lock, self.db_cursor.fetchall())
    
    def validate_lock(self, rel_path, urn):
        '''Check that a lock with the specified urn exists and that it applies
        to path specified by rel_path. Returns True or False.
        '''
        self._sql_query('SELECT * FROM locks WHERE urn = ?', (urn, ))
        row = self.db_cursor.fetchone()
        
        if row is None:
            return False
        
        lock = Lock(row)
        if rel_path == lock.path:
            return True
        
        if lock.infinite_depth:
            return davutils.path_inside_directory(rel_path, lock.path)
        else:
            return False
    
    def create_lock(self, rel_path, shared, owner, depth, timeout):
        '''Create a lock for the resource defined by rel_path. Arguments
        are as follows:
        rel_path: full path to the resource in local file system
        shared: True for shared lock, False for exclusive lock
        owner: client-provided <DAV:owner> xml string describing the owner of the lock
        depth: -1 for infinite, 0 otherwise
        timeout: Client-requested lock expiration time in seconds from now.
                 Configuration may limit actual timeout.
        
        Returns a Lock object.
        '''
        assert depth in [-1, 0]
        assert not rel_path.startswith('/')
        
        urn = uuid4().urn
        timeout = min(timeout, config.lock_max_time) or config.lock_max_time
        valid_until = datetime.datetime.utcnow()
        valid_until += datetime.timedelta(seconds = timeout)
        
        self._sql_query('BEGIN IMMEDIATE TRANSACTION')
        
        try:
            for lock in self.get_locks(rel_path, depth == -1):
                if not lock.shared or not shared:
                    # Allow only one exclusive lock
                    raise DAVError('423 Locked')
            
            self._sql_query('INSERT INTO locks VALUES (?,?,?,?,?,?)',
                (urn, rel_path, bool(shared), owner, depth == -1, valid_until))
            self._sql_query('END TRANSACTION')
        except:
            self._sql_query('ROLLBACK')
            raise
        
        self._sql_query('SELECT * FROM locks WHERE urn=?', (urn, ))
        return Lock(self.db_cursor.fetchone())
        
    def release_lock(self, rel_path, urn):
        '''Remove a lock from database. The rel_path must match a lock
        with the specified urn.
        '''
        
        self._sql_query('BEGIN IMMEDIATE TRANSACTION')
        try:
            if not self.validate_lock(rel_path, urn):
                raise DAVError('409 Conflict',
                               '<DAV:lock-token-matches-request-uri/>')
            
            self._sql_query('DELETE FROM locks WHERE urn=?', (urn, ))
            self._sql_query('END TRANSACTION')
        except:
            self._sql_query('ROLLBACK')
            raise

    def refresh_lock(self, rel_path, urn, timeout):
        '''Refresh the given lock and return new Lock object.'''
        timeout = min(timeout, config.lock_max_time) or config.lock_max_time
        valid_until = datetime.datetime.utcnow()
        valid_until += datetime.timedelta(seconds = timeout)
        
        self._sql_query('BEGIN IMMEDIATE TRANSACTION')
        try:
            if not self.validate_lock(rel_path, urn):
                raise DAVError('412 Precondition Failed',
                               '<DAV:lock-token-matches-request-uri/>')
            
            self._sql_query('UPDATE locks SET valid_until=? WHERE urn=?',
                (valid_until, urn))
            self._sql_query('END TRANSACTION')
        except:
            self._sql_query('ROLLBACK')
            raise
        
        self._sql_query('SELECT * FROM locks WHERE urn=?', (urn, ))
        return Lock(self.db_cursor.fetchone())

if __name__ != '__main__':
    import webdavconfig as config
else:
    import os, time, tempfile
    print "Unit tests"
    
    class config:
        '''Configuration for unit testing'''
        root_dir = '/tmp'
        lock_db = tempfile.mktemp()
        lock_max_time = 3600
        lock_wait = 5
    
    print 'Tempfile is', config.lock_db
    
    # Test basic access
    mgr1 = LockManager()
    
    lock1 = mgr1.create_lock('testfile', False, '', 0, 100)
    
    try:
        assert not mgr1.create_lock('testfile', False, '', 0, 100)
    except DAVError:
        pass
    
    mgr2 = LockManager()
    try:
        assert not mgr2.create_lock('testfile', True, '', 0, 100)
    except DAVError:
        pass
    
    lock2 = mgr1.create_lock('testfile2', True, '', -1, 100)
    lock3 = mgr2.create_lock('testfile2', True, '', -1, 100)
    
    assert mgr1.validate_lock(lock2.path, lock2.urn)
    assert mgr2.validate_lock(lock2.path, lock2.urn)
    
    try:
        assert not mgr1.create_lock('testfile2/subdir', False, '', 0, 100)
    except DAVError:
        pass
    
    try:
        assert not mgr1.create_lock('', False, '', -1, 100)
    except DAVError:
        pass
    
    lock4 = mgr1.create_lock('testdir/testfile3', False, '', -1, 100)
    assert mgr1.get_locks('testdir', True) == [lock4]
    
    mgr1.release_lock(lock1.path, lock1.urn)
    mgr1.release_lock(lock2.path, lock2.urn)
    mgr1.release_lock(lock3.path, lock3.urn)
    
    assert not mgr1.validate_lock(lock1.path, lock1.urn)
    
    # Test lock timeouts
    lock1 = mgr1.create_lock('testfile', False, '', 0, 2)
    lock2 = mgr1.create_lock('testfile2', False, '', 0, 2)
    
    time.sleep(1)
    mgr1.refresh_lock(lock1.path, lock1.urn, 10)
    time.sleep(2)
    
    mgr2 = LockManager()
    assert mgr2.validate_lock(lock1.path, lock1.urn)
    assert not mgr2.validate_lock(lock2.path, lock2.urn)
    
    os.unlink(config.lock_db)
    
    print "Unit tests OK"
    
    