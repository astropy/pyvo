#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.dal.tap
"""
from __future__ import print_function, division

import os, sys, shutil, re, imp, glob, tempfile, random, time
import unittest, pdb
from urllib2 import URLError, HTTPError

import pyvo.dal.query as dalq
import pyvo.dal.tap as tap
import pyvo.dal.dbapi2 as daldbapi
# from astropy.io.vo import parse as votableparse
from astropy.io.votable.tree import VOTableFile
from pyvo.dal.query import _votableparse as votableparse
from astropy.utils.data import get_pkg_data_filename
from . import aTestSIAServer as testserve

tapresultfile = "data/arihip-tap.xml"
errresultfile = "data/error-tap.xml"
uploadfile = "data/upload-tap.xml"
testserverport = 8084
testserverport += 50
testserverport += random.randint(0,9)

class TAPServiceTest(unittest.TestCase):

    baseurl = "http://localhost/sia"

    def testCtor(self):
        self.srv = tap.TAPService(self.baseurl)

    def testProps(self):
        self.testCtor()

        self.assertEquals(self.srv.baseurl, self.baseurl)
        self.assertEquals(self.srv.protocol, "tap")
        try:
            self.srv.baseurl = "towel"
            self.fail("baseurl not read-only")
        except AttributeError:
            pass

class TAPRunTest(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        cls.srvr = testserve.get_server(testserverport)
        cls.srvr.start()
        time.sleep(0.5)

    @classmethod
    def teardown_class(cls):
        if cls.srvr.isAlive():
            cls.srvr.shutdown()
        if cls.srvr.isAlive():
            print("prob")

    def testRunSync(self):
        query = "SELECT TOP 1 1+1 AS result FROM arihip.main"

        s = tap.TAPService("http://localhost:{0}/tap".format(self.srvr.port))

        r = s.run_sync(query)

        self.assert_(isinstance(r, tap.TAPResults))
        self.assert_(r.query_status == "OVERFLOW")
        self.assert_(len(r) == 1)

    def testRunAsync(self):
        query = "SELECT TOP 1 1+1 AS result FROM arihip.main"

        s = tap.TAPService("http://localhost:{0}/tap".format(self.srvr.port))
        q = s.run_async(query)

        self.assert_(isinstance(q, tap.AsyncTAPJob))

        q.run()

        r = q.execute()

        self.assert_(isinstance(r, tap.TAPResults))
        self.assert_(r.query_status == "OVERFLOW")
        self.assert_(len(r) == 1)


__all__ = "TAPServiceTest TAPRunTest".split()
def suite():
    tests = []
    for t in __all__:
        tests.append(unittest.makeSuite(globals()[t]))
    return unittest.TestSuite(tests)

if __name__ == "__main__":
    try:
        module = find_current_module(1, True)
        pkgdir = os.path.dirname(module.__file__)
        t = "aTestSIAServer"
        mod = imp.find_module(t, [pkgdir])
        testserve = imp.load_module(t, mod[0], mod[1], mod[2])
    except ImportError as e:
        sys.stderr.write("Can't find test server: aTestSIAServer.py:"+str(e))

    srvr = testserve.TestServer(testserverport)

    try:
        srvr.start()
        unittest.main()
    finally:
        if srvr.isAlive():
            srvr.shutdown()
