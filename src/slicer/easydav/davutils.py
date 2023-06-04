# -*- coding: utf-8 -*-

'''Miscellaneous DAV-related utility functions and their associated unit
tests.
'''

import mimetypes
import time
import os.path
import re
from fnmatch import fnmatchcase

class DAVError(Exception):
    '''A protocol exception that is passed to client through HTTP.
    Two properties:
    - httpstatus: e.g. '404 Not Found'
    - body: None or e.g. '<DAV:cannot-modify-protected-property/>'
    
    Argument httpstatus is passed to WebDAV client as HTTP status code.
    Body can optionally be an XML response body; otherwise,
    exception handler generates an text/plain response of the
    status code.
    '''
    def __init__(self, httpstatus, body = None):
        Exception.__init__(self, httpstatus)
        self.httpstatus = str(httpstatus)
        self.body = body and str(body)
    
    def __str__(self):
        return self.httpstatus
    
    def __repr__(self):
        return ('DAVError(' + repr(self.httpstatus) +
                ', ' + repr(self.body) + ')')
    
    def __eq__(self, other):
        return (isinstance(other, DAVError)
                and self.httpstatus == other.httpstatus
                and self.body == other.body)
    
    def __hash__(self):
        return hash(self.httpstatus) ^ hash(self.body)

def read_blocks(source, count = None, blocksize = 1024*1024):
    '''Read and yield block-sized strings from open file object,
    up to a total of count bytes.
    '''
    while count is None or count > 0:
        if count is not None:
            blocksize = min(count, blocksize)

        data = source.read(blocksize)
        
        if len(data) == 0:
            return # End of file
        
        if count is not None:
            count -= len(data)
        
        yield data

def write_blocks(dest, blocks):
    '''Write a series of blocks to open file object.'''
    for block in blocks:
        dest.write(block)

def path_inside_directory(path, root):
    '''Check if path is inside root directory.
    '''
    path_parts = os.path.abspath(path).split(os.path.sep)
    root_parts = os.path.abspath(root).split(os.path.sep)
    
    if root_parts == ['', '']:
        root_parts = [''] # When root is '/', split gives '',''
    
    return path_parts[:len(root_parts)] == root_parts

def get_relpath(path, root):
    '''Get the relative path after the root path.
    This differs from os.path.relpath slightly:
    - The result never has trailing or leading / or ..
    - The result is empty string if path == root
    - Path must be inside root directory.
    '''
    path_parts = os.path.abspath(path).split(os.path.sep)
    root_parts = os.path.abspath(root).split(os.path.sep)
    
    if root_parts == ['', '']:
        root_parts = [''] # When root is '/', split gives '',''
    
    assert path_parts[:len(root_parts)] == root_parts
    return os.path.sep.join(path_parts[len(root_parts):])

def get_isoformat(timestamp):
    '''Format the timestamp according to ISO8601 / RFC3339.'''
    t = time.gmtime(timestamp)
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', t)

def get_rfcformat(timestamp):
    '''Format the timestamp according to RFC822.'''
    t = time.gmtime(timestamp)
    return time.strftime('%a, %d %b %Y %H:%M:%S %z', t)

def get_usertime(timestamp):
    '''Format the timestamp for reading by user.'''
    t = time.localtime(timestamp)
    return time.strftime('%d-%b-%Y %H:%M:%S', t)

def set_mtime(real_path, rfctime):
    '''Set file modification time based on a RFC822 timestamp.'''
    timestamp = time.strptime(rfctime, '%a, %d %b %Y %H:%M:%S %z')
    os.utime(real_path, (timestamp, timestamp))

def pretty_unit(value, base=1000, minunit=None, format="%0.1f"):
    ''' Finds the correct unit and returns a pretty string
    pretty_unit(4190591051, base=1024) = "3.9 Gi"

    From http://github.com/str4nd/bittivahti/
    '''
    if not minunit:
        minunit = base
    
    # Units based on base
    if base == 1000:
        units = [' ', 'k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']
    elif base == 1024:
        units = [' ', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi']
    else:
        raise ValueError("The unit base has to be 1000 or 1024")
    
    # Divide until below threshold or base
    v = float(value)
    u = base
    for unit in units:
        if v >= base or u <= minunit:
            v = v/base
            u = u * base
        else:
            return format % v + " " + unit

def get_mimetype(real_path):
    '''Use mimetypes module to guess Content-Type for the file.
    If it fails, use application/octet-stream.
    '''
    mimetype = mimetypes.guess_type(real_path)[0]
    if not mimetype:
        mimetype = 'application/octet-stream'
    return mimetype

def create_etag(real_path):
    '''Get an unique identifier for this revision of the file.
    This is used by HTTP clients for caching purposes.
    '''
    return ('"' + str(os.path.getmtime(real_path)) +
        'S' + str(os.path.getsize(real_path)) + '"')

def compare_etags(etag, etag_list):
    '''Compare the specified etag against the list.
    List can be either a single tag, a list separated with comma,
    or an asterisk:
    - '"tag"': matches only if etag == '"tag"'
    - '"tag1", "tag2"': matches if etag in ['"tag1"', '"tag2"']
    - '*': matches any etag
    
    Note: the ETags generated by this application do not contain
    commas. This function can't match against ETags with commas.
    '''
    parts = [e.strip() for e in etag_list.split(',')]
    
    if parts == ['*']:
        return True
    elif etag in parts:
        return True
    else:
        return False

def add_to_dict_list(dictionary, key, item):
    '''Add the item to the list stored in the dictionary with
    the specified key. If the key does not exist, create a new
    list.
    '''
    if not dictionary.has_key(key):
        dictionary[key] = []
    dictionary[key].append(item)

def search_directory(directory, depth = -1):
    '''Find all files and directories under a directory tree,
    yielding paths. Depth is the recursion limit:
        0 == yield just the start directory,
        1 == yield start directory and files there,
        -1 == infinite.
    '''
    
    yield directory
    
    if depth == 0 or not os.path.isdir(directory):
        return
    
    for filename in os.listdir(directory):
        path = os.path.join(directory, filename)
        if os.path.isdir(filename):
            for path in search_directory(path, depth - 1):
                yield path
        else:
            yield path

def add_to_zip_recursively(zipobj, real_path, root_dir, check_read):
    '''Adds the file at real_path, and if it is a directory,
    all files under it to a ZIP archive.
    Filenames are converted from UTF-8 to CP437.
    Root_dir is stripped from beginning of each file name.
    Check_read is a function that returns False for files that
    should not be included in archive.
    '''
    if not root_dir.endswith('/'):
        root_dir += '/'
    
    for path in search_directory(real_path):
        if not os.path.isdir(path) and not check_read(path):
            continue
        
        assert path[:len(root_dir)] == root_dir
        rel_path = path[len(root_dir):]
        rel_path = rel_path.encode('cp437', 'replace')
        zipobj.write(path, rel_path)

def compare_path(real_path, patterns):
    '''Compare a path to a list of patterns.
    Patterns can be either shell glob patterns that
    are compared against each path component,
    or functions that get passed the complete path.
    '''
    real_path = os.path.normpath(real_path)
    parts = real_path.strip('/').split('/')
    
    for pattern in patterns:
        if callable(pattern):
            if pattern(real_path):
                return True
        else:
            for part in parts:
                if fnmatchcase(part, pattern):
                    return True
    
    return False

def parse_if_list(string):
    '''Read a "List" structure as defined in RFC4918
    Returns list of tuples (Type, Invert, Value).
    
    To make parsing easier, state tokens or ETags should not contain any of
    the following characters:
    ()[]<>"
    The state tokens and ETags generated by this program satisfy this rule
    and I don't expect any sane client to pass other values.
    Resource tags can contain anything except >
    
    RFC4918 Section 10.4.2:
    List           = "(" 1*Condition ")"
    Condition      = ["Not"] (State-token | "[" entity-tag "]")
    entity-tag     = [ weak ] opaque-tag
    weak           = "W/"
    opaque-tag     = quoted-string
    quoted-string  = ( <"> *(qdtext | quoted-pair ) <"> )
    qdtext         = <any TEXT except <">>
    quoted-pair    = "\" CHAR
    State-token    = Coded-URL
    Coded-URL      = "<" absolute-URI ">"
    '''

    results = []
    conditions = re.findall(r'(Not)?\s*([<\[][^>\]]+[>\]])', string)
    for c_not, c_tag in conditions:
        if c_tag.startswith('['):
            c_type = 'etag'
            c_tag = c_tag.strip('[]')
        else:
            c_type = 'token'
            c_tag = c_tag.strip('<>')
        
        results.append((c_type, bool(c_not), c_tag))
    
    return results

def parse_if_header(if_header):
    '''Parse a HTTP If: -header. Returns a list of tuples of resource url and
    conditions. Each condition is a tuple of (Type, Invert, Value), where:
    Type is 'etag' or 'token', Invert is True or False and Value is a string.
    
    Each list of conditions must match completely, and any of the
    tuples in the top-most list must match.
    
    parse_if_header(
        '(<urn:uuid:181d4fae-7d8c-11d0-a765-00a0c91e6bf2> '
        + '["I am an ETag"]) (["I am another ETag"])')
    
    should give:
    
    [(None, 
        [('token', False, 'urn:uuid:181d4fae-7d8c-11d0-a765-00a0c91e6bf2'),
         ('etag', False, '"I am an ETag"')]),
     (None,
        [('etag', False, '"I am another ETag"')])
    ]
    
    RFC4918:
    If = "If" ":" ( 1*No-tag-list | 1*Tagged-list ) 
    No-tag-list = List
    Tagged-list = Resource-Tag 1*List
    List = "(" 1*Condition ")"
    Resource-Tag = "<" Simple-ref ">" 
    '''
    
    if_header = if_header.strip()
    if if_header[0] == '(':
        no_tag = True
        lists = re.findall(r'()\(([^\)]+)\)', if_header)
    else:
        no_tag = False
        # Group 1: Resource-Tag, Group 2: List contents
        lists = re.findall(r'<([^>]+)>\s*\(([^\)]+)\)', if_header)
    
    results = []
    for l_tag, l_contents in lists:
        if no_tag:
            l_tag = None
        results.append((l_tag, parse_if_list(l_contents)))
    return results

def parse_timeout(value):
    '''Parses a TimeType construction, returning timeout in seconds or
    None for infinity. Invalid strings return ValueError.
    '''
    value = value.strip()
    if value == 'Infinite':
        return None
    elif value.startswith('Second-'):
        return int(value[len('Second-'):])
    else:
        raise ValueError('Unknown timeout type')

if __name__ == '__main__':
    print "Unit tests"
    
    assert path_inside_directory('/tmp/foobar', '/tmp')
    assert path_inside_directory('/', '/')
    assert path_inside_directory('/foobar', '/')
    assert path_inside_directory('foobar', '')
    assert not path_inside_directory('/', '/tmp')
    assert not path_inside_directory('/tmp/../tmp/..', '/tmp')
    assert not path_inside_directory('..', '')
    
    assert get_relpath('/tmp/foobar', '/tmp') == 'foobar'
    assert get_relpath('/tmp/', '/tmp') == ''
    assert get_relpath('/foobar', '/') == 'foobar'
    
    test_dict = {}
    add_to_dict_list(test_dict, 'ankka', 'heppa')
    add_to_dict_list(test_dict, 'ankka', 'koira')
    assert test_dict['ankka'] == ['heppa', 'koira']
    
    assert compare_etags('"foo"', '"foo"')
    assert not compare_etags('"foo"', '"foo2"')
    assert compare_etags('"foo"', '"foo", "foo2"')
    assert compare_etags('"foo"', '"foo2","foo"')
    assert compare_etags('"foo"', '*')
    assert not compare_etags('"foo"', '')
    
    assert compare_path('/tmp/.svn/foo', ['foo'])
    assert not compare_path('/tmp/.svn/foo2', ['foo'])
    assert compare_path('/tmp/.svn/foo', ['.svn'])
    assert compare_path('/tmp/hack.php', ['*.php'])
    assert compare_path('/tmp/.hack.php', ['*.php'])
    assert compare_path('/tmp/hack.php.txt', ['*.php.*'])
    assert compare_path('/tmp/foo', ['*'])
    
    assert (parse_if_list('(["Foobar"]Not["foobar"])') ==
            [('etag', False, '"Foobar"'), ('etag', True, '"foobar"')])
    
    assert (parse_if_header(
            '(<urn:uuid:181d4fae-7d8c-11d0-a765-00a0c91e6bf2> '
            + '["I am an ETag"]) (["I am another ETag"])')
        ==  [(None, 
                [('token', False, 'urn:uuid:181d4fae-7d8c-11d0-a765-00a0c91e6bf2'),
                ('etag', False, '"I am an ETag"')]),
            (None,
                [('etag', False, '"I am another ETag"')])
            ])
    
    assert (parse_if_header(
            r'''<http://user:pass@test.com/~-._%20!$&'()*+,;=> (["Etagfoo"])''')
        ==  [(r'''http://user:pass@test.com/~-._%20!$&'()*+,;=''',
                [('etag', False, r'"Etagfoo"')])
            ])
    
    assert (parse_if_header('<foo>(Not["Etag"])')
        == [('foo', [('etag', True, '"Etag"')])])

    assert parse_timeout('Second-1234') == 1234
    assert parse_timeout('Infinite') is None

    print "Unit tests OK"
    