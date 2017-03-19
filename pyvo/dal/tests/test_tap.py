#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.dal.tap
"""
from __future__ import (
    absolute_import, division, print_function, unicode_literals)

import os, sys, shutil, re, imp, glob, tempfile, random, time
import unittest, pdb
import os.path

import pyvo.dal.query as dalq
import pyvo.dal.tap as tap
import pyvo.dal.dbapi2 as daldbapi
# from astropy.io.vo import parse as votableparse
from astropy.io.votable.tree import VOTableFile
from astropy.io.votable import parse as votableparse
from astropy.utils.data import get_pkg_data_filename
from . import testserver

tapresultfile = os.path.join(os.path.dirname(__file__), "data/arihip-tap.xml")
errresultfile = "data/error-tap.xml"
uploadfile = "data/upload-tap.xml"
testserverport = 8084

class TAPServiceTest(unittest.TestCase):

    baseurl = "http://localhost/tap"

    def testCtor(self):
        self.srv = tap.TAPService(self.baseurl)

    def testProps(self):
        self.testCtor()

        self.assertEquals(self.srv.baseurl, self.baseurl)
        try:
            self.srv.baseurl = "towel"
            self.fail("baseurl not read-only")
        except AttributeError:
            pass

class TAPRunTest(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        cls.srvr = testserver.get_server(testserverport)
        cls.srvr.start()
        time.sleep(0.5)

    @classmethod
    def teardown_class(cls):
        if cls.srvr.is_alive():
            cls.srvr.terminate()

    def testRunSync(self):
        query = "SELECT TOP 1 1+1 AS result FROM arihip.main"

        s = tap.TAPService("http://localhost:{0}/tap".format(self.srvr.port))

        r = s.run_sync(query)

        self.assertIsInstance(r, tap.TAPResults)
        self.assertEquals(r.query_status, "OVERFLOW")
        self.assert_(len(r) == 1)

    def testRunAsync(self):
        query = "SELECT TOP 1 1+1 AS result FROM arihip.main"

        s = tap.TAPService("http://localhost:{0}/tap".format(self.srvr.port))

        r = s.run_async(query)

        self.assertIsInstance(r, tap.TAPResults)
        self.assertEquals(r.query_status, "OVERFLOW")
        self.assert_(len(r) == 1)

    def testRunSyncUpload(self):
        query = "SELECT * FROM TAP_UPLOAD.t1"

        s = tap.TAPService("http://localhost:{0}/tap".format(self.srvr.port))

        r = s.run_sync(query, uploads = {'t1': open(tapresultfile)})

        self.assertIsInstance(r, tap.TAPResults)
        self.assertEquals(r.query_status, "OVERFLOW")
        self.assert_(len(r) == 1)

    def testRunAsyncUpload(self):
        query = "SELECT * FROM TAP_UPLOAD.t1"

        s = tap.TAPService("http://localhost:{0}/tap".format(self.srvr.port))

        r = s.run_async(query,
            uploads = {'t1': open(tapresultfile)})

        self.assertIsInstance(r, tap.TAPResults)
        self.assertEquals(r.query_status, "OVERFLOW")
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
        t = "testserver"
        mod = imp.find_module(t, [pkgdir])
        testserve = imp.load_module(t, mod[0], mod[1], mod[2])
    except ImportError as e:
        sys.stderr.write("Can't find test server: testserver.py:" + str(e))

    srvr = testserver.TestServer(testserverport)

    try:
        srvr.start()
        unittest.main()
    finally:
        if srvr.is_alive():
            srvr.terminate()
