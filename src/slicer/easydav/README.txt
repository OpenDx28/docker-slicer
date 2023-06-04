% EasyDAV - A simple to deploy WSGI webdav implementation.

License
-------

Copyright 2010-2012 Petteri Aimonen <jpa at wd.mail.kapsi.fi>

Redistribution and use in source and binary forms, with or without modification, are
permitted provided that the following conditions are met:

   1. Redistributions of source code must retain the above copyright notice, this list of
      conditions and the following disclaimer.

   2. Redistributions in binary form must reproduce the above copyright notice, this list
      of conditions and the following disclaimer in the documentation and/or other materials
      provided with the distribution.


System Requirements
-------------------

EasyDAV requires Python 2.5 or newer (but not 3.x), the Kid template library
and flup WSGI library. Flup can also easily be replaced with any other
WSGI-compatible library.

Debian packages required:
python python-kid python-flup

Installation
------------

First create a configuration file for the script by copying webdavconfig.py.example
to webdavconfig.py. You must set atleast *root_dir* in this file. This is
the filesystem path to the root folder that will contain the files accessible
through WebDAV.

Possible deployment methods are:

1) A standalone server, using wsgiref package. Mostly for testing purposes.
   
   Just run webdav.py. The server will be on http://localhost:8080/.
   Port and host can be changed in the end of webdav.py.

2) A normal CGI script under Apache or other webserver.

   Copy the files to a folder under webserver document root, for example
   to ~/public_html/webdav. Copy htaccess_example.txt to .htaccess and
   change the *RewriteBase* in this file.

   Alternatively, don't create .htaccess and you can access the directory
   with the url http://domain.com/~user/webdav/webdav.cgi/. In that case
   you might want to take steps to protect webdavconfig.py from access
   through web server, by e.g. setting chmod 700.

3) An FCGI script under Apache or other webserver.

   Do as in 2), and after verifying functionality, change the script name
   in .htaccess to *webdav.fcgi*. Note that when using FCGI, any changes
   you make to webdavconfig.py don't come to effect until you kill the process.

Configuration file
------------------

The configuration file, *webdavconfig.py*, has the following settings:
- *root_dir:*
  The file system path to the directory where files will be stored.
- *root_url:*
  Complete url to the repository on web, or None to decide automatically.
- *restrict_access:*
  List of file name patterns that can not be accessed at all, not read not
  written. They also won't show up in directory listings.
- *restrict_write:*
  List of files that cannot be written. These will show up in directory listing.
  They cannot be directly copied or removed, but can be when the action is
  performed on a whole directory.
- *unicode_normalize:*
  Normalization of unicode characters used in file names. Ensures that all clients
  threat semantically equivalent filenames as logically equivalent.
- *lock_db:*
  SQLite database file to store acquired locks. Set to None to disable locking.
- *lock_max_time:*
  Maximum expire time of locks, in seconds.
- *lock_wait:*
  Time to wait for access to lock database, in seconds.
- *log_file:*
  Log file name relative to webdav.py location.
- *log_level:*
  Numerical value, 0 for maximum amount of debug messages.

Security
--------

You should protect access to the WebDAV repository by using HTTP Authentication,
with for example Apache mod_auth. Most WebDAV clients support HTTPS and Digest
authentication, so use either of them so that passwords are not transmitted
in plain text.

Every effort has been taken to protect the script from accessing files outside
*root_dir*. The worst the WebDAV users can do is fill up the hard drive.

When the root directory is accessible through web server (like when managing
web pages through WebDAV), users might upload an executable file. The default
configuration prohibits writing to .php, .pl, .cgi and .fcgi files. You should
add any other extensions recognized by your web server.

Test method
-----------

Each release is tested automatically in the following configurations:

1) Stand-alone through Python's SimpleHTTPServer (by running webdav.py).
2) Under Apache vhost with FCGI interface.
3) Under Apache userdir with CGI interface.

Currently automatic testing includes the litmus WebDAV test suite, which aims
to verify standard compatibility. The features required by test set "props"
are currently not supported.
http://www.webdav.org/neon/litmus/

Automatic regression tests for the security features are planned but not yet
implemented. Unit tests for the part are implemented.

Configurations 2) or 3) above are preferred for client compatibility testing.
The test method is as follows:

1) Download the test file set from http://kapsi.fi/~jpa/stuff/other/testfiles.tar.gz
   and extract it. Verify that the filenames are correct:
    Test file set
    Test file set/100Mnull
    Test file set/Pictures
    Test file set/Pictures/Chýnovská_jeskyně(4).jpg
    Test file set/Pictures/Hawaiian Eruption-numbers.svg
    Test file set/Pictures/Laufwasserkraftwerk Muehltal.jpg
    Test file set/Pictures/Monarch Butterfly Danaus plexippus Feeding Down 3008px.jpg
    Test file set/ÅÄÖåäö
    Test file set/ÅÄÖåäö/Empty file.txt.txt
2) Mount the WebDAV directory.
3) Copy all test files to the WebDAV directory.
4) Using the WebDAV client, copy 'Test file set' to another name.
5) Using the WebDAV client, rename 'Test file set' to 'Test file set after move'.
6) Verify that the special characters in file names display the same way through
   WebDAV client as they do on the local system.
7) Using a web browser, check that the file names display correctly in the HTML
   interface. This verifies that the character set is correct on the server side
   also.
8) If the WebDAV client emulates filesystem access, open one of the
   pictures in a image viewer.
9) Using the WebDAV client, download the 'Test file set after move' back to local
   system. Verify that the contents are identical to the original test file set.
10) Using the WebDAV client, remove both folders from the server.

Any errors at any point of the procedure should be noted in the client support
table.

Known bugs
----------
When using the built-in wsgiref.simple_server, the chunked encoding used by
Mac OS X client is not supported. It is supported under CGI and FCGI.

File timestamps are not preserved while uploading. May depend on client.

Missing features
----------------
The server supports only predefined properties. Custom properties cannot be set
and therefore the litmus testset 'props' fails.

The server does not support per-user access restrictions. These could be
implemented by hacking the code in requestinfo.py.

