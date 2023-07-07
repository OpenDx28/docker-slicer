# -*- coding: utf-8 -*-

import logging

class WSGIInputWrapper:
    '''Resolves an issue with WSGI and various servers. If the WSGI application
    does not read from input, the server may give an error such as:
    "(104)Connection reset by peer: ap_content_length_filter:
    apr_bucket_read() failed"
    
    Also unifies the interface so that read() without arguments always works.
    Normally the wsgiref.simple_server does not support it and CONTENT_LENGTH
    must be used. In contrast, under Apache, you have to use read() to get
    body for Transfer-encoding: chunked requests.
    
    Suggested use:
    environ['wsgi.input'] = WSGIInputWrapper(environ)
    and after any handler has run:
    environ['wsgi.input'].read()
    '''
    
    def __init__(self, environ):
        self.length = self.get_length(environ)
        self.bytes_read = 0
        self.wsgi_input = environ['wsgi.input']
    
    def get_length(self, environ):
        '''Get length of request body or -1 if the client uses chunked encoding.
        '''
        if environ.get('TRANSFER_ENCODING', '').lower() == 'chunked':
            return -1
        elif environ.get('CONTENT_LENGTH'):
            try:
                return int(environ['CONTENT_LENGTH'])
            except ValueError:
                # This doesn't throw exception, because handling the exception
                # would be difficult if we can't handle the input reading.
                logging.warning('Invalid Content-Length: '
                    + repr(environ['CONTENT_LENGTH']))
                return 0
        else:
            return 0
    
    def read(self, count = -1):
        '''Read up to count bytes from wsgi.input, or until EOF is count is -1.'''
        if self.length == -1:
            result = self.wsgi_input.read(count)
        else:
            bytes_left = self.length - self.bytes_read
            if bytes_left <= 0 or count == 0:
                result = ''
            elif count == -1:
                result = self.wsgi_input.read(bytes_left)
            else:
                result = self.wsgi_input.read(min(bytes_left, count))

        self.bytes_read += len(result)
        return result

    def readline(self, size = -1):
        result = self.wsgi_input.readline(size)
        self.bytes_read += len(result)
        return result
