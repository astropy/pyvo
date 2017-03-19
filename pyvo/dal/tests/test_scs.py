#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.dal.scs
"""
from __future__ import (
    absolute_import, division, print_function, unicode_literals)

import os, sys, shutil, re, imp, random, time
import unittest, pdb

import pyvo.dal.query as dalq
from pyvo.dal import scs as cs
import pyvo.dal.dbapi2 as daldbapi
# from astropy.io.vo import parse as votableparse
from astropy.io.votable.exceptions import W22
from astropy.io.votable import parse as votableparse
from astropy.utils.data import get_pkg_data_filename
from astropy.coordinates import SkyCoord
from . import testserver

csresultfile = "data/twomass-cs.xml"
errresultfile = "data/error-cs.xml"
testserverport = 8084
testserverport += 20
testserverport += random.randint(0,9)

class SCSServiceTest(unittest.TestCase):

    baseurl = "http://localhost/cs"
    srv = None

    def testCtor(self):
        self.srv = cs.SCSService(self.baseurl)

    def testProps(self):
        self.testCtor()
        self.assertEquals(self.srv.baseurl, self.baseurl)

    def testCreateQuery(self):
        self.testCtor()
        q = self.srv.create_query()
        self.assertIsInstance(q, cs.SCSQuery)
        self.assertEquals(q.baseurl, self.baseurl)
        self.assertEquals(len(q.keys()), 0)

    def testCreateQueryWithArgs(self):
        self.testCtor()
        q = self.srv.create_query(pos=(0.0, 0.0), radius=1.0, verbosity=2)
        self.assert_(isinstance(q, cs.SCSQuery))
        self.assertEquals(q.baseurl, self.baseurl)
        self.assertEquals(len(q.keys()), 4)

        self.assertEquals(q.pos, (0.0, 0.0))
        self.assertEquals(q.radius, 1.0)
        self.assertEquals(q.verbosity, 2)


class SCSQueryTest(unittest.TestCase):

    baseurl = "http://localhost/cs"

    def testCtor(self):
        self.q = cs.SCSQuery(self.baseurl)
        self.assertEquals(self.q.baseurl, self.baseurl)

    def testPos(self):
        self.testCtor()
        self.assert_(self.q.pos is None)
        self.assert_(self.q.radius is None)

        self.q.pos = (120.445, 40.1434)
        self.assertEquals(self.q.pos, (120.445, 40.1434))

        self.q.radius = 0.25
        self.assertEquals(self.q.radius, 0.25)

        self.q.pos = (400.0, -60.0)
        self.assertEquals(self.q.pos, (400.0, -60.0))

    def testCreateURL(self):
        self.testCtor()
        self.assertEquals(self.q.queryurl, self.baseurl)

        self.q.pos = (102.5511, 24.312)
        self.q.radius = 0.1
        self.assertAlmostEquals(self.q["RA"], 102.5511)
        self.assertAlmostEquals(self.q["DEC"], 24.312)
        self.assertAlmostEquals(self.q["SR"], 0.1)

        self.q.radius = 0.05
        self.assertAlmostEquals(self.q["SR"], 0.05)


class CSResultsTest(unittest.TestCase):

    def setUp(self):
        resultfile = get_pkg_data_filename(csresultfile)
        self.tbl = votableparse(resultfile)

    def testCtor(self):
        self.r = cs.SCSResults(self.tbl)
        self.assertIsInstance(self.r._fldnames, list)
        self.assertIsNotNone(self.r.votable)
        self.assertEquals(len(self.r), 2)

    def testGetRecord(self):
        self.testCtor()
        rec = self.r.getrecord(0)
        self.assertIsInstance(rec, cs.SCSRecord)


class CSResultsErrorTest(unittest.TestCase):

    def testErrorVOTableInfo(self):
        resultfile = get_pkg_data_filename(errresultfile)
        self.tbl = votableparse(resultfile)
        try:
            res = cs.SCSResults(self.tbl)
            self.fail("Failed to detect error response")
        except dalq.DALQueryError as ex:
            self.assertEquals(ex.label, "Error")
            self.assertEquals(ex.reason, "Forced Fail")

    def testErrorResourceInfo(self):
        resultfile = get_pkg_data_filename("data/error3-cs.xml")
        self.tbl = votableparse(resultfile)
        try:
            res = cs.SCSResults(self.tbl)
            self.fail("Failed to detect error response")
        except dalq.DALQueryError as ex:
            self.assertEquals(ex.label, "Error")
            self.assertEquals(ex.reason, "Forced Fail")

    def testErrorParam(self):
        resultfile = get_pkg_data_filename("data/error2-cs.xml")
        self.tbl = votableparse(resultfile)
        try:
            res = cs.SCSResults(self.tbl)
            self.fail("Failed to detect error response")
        except dalq.DALQueryError as ex:
            self.assertEquals(ex.label, "Error")
            # Note: because it is stored in a PARAM and the datatype is "char",
            # the value will come out as bytes (rather than unicode)
            self.assertEquals(ex.reason, b"DEC parameter out-of-range")

#    def testErrorDefParam(self):
#       Will not raise if VOTable version is 1.0
    def _testErrorDefParam(self):
        resultfile = get_pkg_data_filename("error4-cs.xml")
        self.assertRaises(W22, votableparse, resultfile)


class CSRecordTest(unittest.TestCase):

    def setUp(self):
        resultfile = get_pkg_data_filename(csresultfile)
        self.tbl = votableparse(resultfile)
        self.result = cs.SCSResults(self.tbl)
        self.rec = self.result.getrecord(0)

    def testAttr(self):
        self.assertEquals(self.rec.pos.ra.value, 0.065625)
        self.assertEquals(self.rec.pos.dec.value, -8.8911667)
        self.assertEquals(self.rec.id, b"34")

class CSExecuteTest(unittest.TestCase):
    baseurl = "http://localhost:{0}/cs?"

    srvr = None

    @classmethod
    def setup_class(cls):
        cls.srvr = testserver.get_server(testserverport)
        cls.srvr.start()
        time.sleep(0.5)

    @classmethod
    def teardown_class(cls):
        if cls.srvr.is_alive():
            cls.srvr.terminate()
        if cls.srvr.is_alive():
            print("prob")

    def testExecute(self):
        q = cs.SCSQuery(self.baseurl.format(self.srvr.port))
        q.pos = (0.0, 0.0)
        q.radius = 0.25
        results = q.execute()
        self.assertIsInstance(results, cs.SCSResults)
        self.assertEquals(len(results), 2)

    def testSearch(self):
        srv = cs.SCSService(self.baseurl.format(self.srvr.port))
        results = srv.search(pos=(0.0, 0.0), radius=0.25)
        self.assertIsInstance(results, cs.SCSResults)
        self.assertEquals(len(results), 2)

    def testConesearch(self):
        results = cs.search(
            self.baseurl.format(self.srvr.port), pos=(0.0, 0.0), radius=0.25)
        self.assert_(isinstance(results, cs.SCSResults))
        self.assertEquals(len(results), 2)


__all__ = "SCSServiceTest SCSQueryTest CSResultsTest CSRecordTest CSExecuteTest".split()
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
        testserver = imp.load_module(t, mod[0], mod[1], mod[2])
    except ImportError as e:
        sys.stderr.write("Can't find test server: testserver.py:"+str(e))

    srvr = testserver.TestServer(testserverport)

    try:
        srvr.start()
        unittest.main()
    finally:
        if srvr.is_alive():
            srvr.terminate()
