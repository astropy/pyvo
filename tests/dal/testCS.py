#!/usr/bin/env python
"""
Tests for vaopy.dal.conesearch
"""
import os, sys, shutil, re, imp
import unittest, pdb
from urllib2 import URLError, HTTPError

import vaopy.dal.query as dalq
import vaopy.dal.conesearch as cs
import vaopy.dal.dbapi2 as daldbapi
# from astropy.io.vo import parse as votableparse
from astropy.io.vo.tree import VOTableFile
from astropy.io.vo.exceptions import W22
from vaopy.dal.query import _votableparse as votableparse

testdir = os.path.dirname(sys.argv[0])
if not testdir:  testdir = "tests"
csresultfile = "twomass-cs.xml"
errresultfile = "error-cs.xml"
testserverport = 8081

try:
    t = "aTestSIAServer"
    mod = imp.find_module(t, [testdir])
    testserver = imp.load_module(t, mod[0], mod[1], mod[2])
    testserver.testdir = testdir
except ImportError, e:
    print >> sys.stderr, "Can't find test server: aTestSIAServer.py:", str(e)

class CSServiceTest(unittest.TestCase):

    baseurl = "http://localhost/cs"

    def testCtor(self):
        self.res = {"title": "Archive", "shortName": "arch"}
        self.srv = cs.CSService(self.baseurl, self.res)

    def testProps(self):
        self.testCtor()
        self.assertEquals(self.srv.baseurl, self.baseurl)
        try:
            self.srv.baseurl = "goober"
            self.fail("baseurl not read-only")
        except AttributeError:
            pass

        self.assertEquals(self.srv.description["title"], "Archive")
        self.assertEquals(self.srv.description["shortName"], "arch")
        self.srv.description["title"] = "Sir"
        self.assertEquals(self.res["title"], "Archive")

    def testCreateQuery(self):
        self.testCtor()
        q = self.srv.createQuery()
        self.assert_(isinstance(q, cs.CSQuery))
        self.assertEquals(q.baseurl, self.baseurl)
        self.assertEquals(len(q._param.keys()), 0)

    def testCreateQueryWithArgs(self):
        self.testCtor()
        q = self.srv.createQuery(ra=0.0, dec=0.0, sr=1.0, verbosity=2)
        self.assert_(isinstance(q, cs.CSQuery))
        self.assertEquals(q.baseurl, self.baseurl)
        self.assertEquals(len(q._param.keys()), 4)

        self.assertEquals(q.ra,  0.0)
        self.assertEquals(q.dec, 0.0)
        self.assertEquals(q.sr,  1.0)
        self.assertEquals(q.verbosity, 2)

        qurl = q.getQueryURL()
        self.assert_("RA=0.0" in qurl)
        self.assert_("DEC=0.0" in qurl)
        self.assert_("SR=1.0" in qurl)
        self.assert_("VERB=2" in qurl)


class CSQueryTest(unittest.TestCase):

    baseurl = "http://localhost/cs"

    def testCtor(self):
        self.q = cs.CSQuery(self.baseurl)

    def testPos(self):
        self.testCtor()
        self.assert_(self.q.ra is None)
        self.assert_(self.q.dec is None)
        self.assert_(self.q.sr is None)

        self.q.ra = 120.445
        self.assertEquals(self.q.ra, 120.445)
        self.q.dec = 40.1434
        self.assertEquals(self.q.dec, 40.1434)
        self.q.sr = 0.25
        self.assertEquals(self.q.sr, 0.25)

        self.q.ra = 400.0
        self.assertEquals(self.q.ra, 40.0)
        self.q.ra = -60.0
        self.assertEquals(self.q.ra, 300.0)


    def testBadPos(self):
        self.testCtor()
        try:  self.q.ra = "a b";  self.fail("ra took string values")
        except ValueError:  pass
        try:  self.q.dec = "a b"; self.fail("dec took string values")
        except ValueError:  pass
        try:  self.q.sr = "a b";  self.fail("dec took string values")
        except ValueError:  pass
        try:  self.q.dec = 100; self.fail("dec took out-of-range value")
        except ValueError, e:  pass
            
    def testCreateURL(self):
        self.testCtor()
        self.q.ra = 102.5511
        qurl = self.q.getQueryURL(lax=True)
        self.assertEquals(qurl, self.baseurl+"?RA=102.5511")

        self.assertRaises(dalq.DalQueryError, self.q.getQueryURL)

        self.q.dec = 24.312
        self.q.sr = 0.1
        qurl = self.q.getQueryURL()
        self.assert_("RA=102.5511" in qurl)
        self.assert_("DEC=24.312" in qurl)
        self.assert_("SR=0.1" in qurl)


class CSResultsTest(unittest.TestCase):

    def setUp(self):
        resultfile = os.path.join(testdir, csresultfile)
        self.tbl = votableparse(resultfile)

    def testCtor(self):
        self.r = cs.CSResults(self.tbl)
        self.assert_(isinstance(self.r._fldnames, list))
        self.assert_(self.r._tbl is not None)
        self.assertEquals(self.r.size, 2)

    def testUCDMap(self):
        self.testCtor()
        self.assertEquals(self.r._cscols["POS_EQ_RA_MAIN"], "RA")
        self.assertEquals(self.r._cscols["POS_EQ_DEC_MAIN"], "DEC")
        self.assertEquals(self.r._cscols["ID_MAIN"], "OBJID")

    def testGetRecord(self):
        self.testCtor()
        rec = self.r.getrecord(0)
        self.assert_(isinstance(rec, cs.CSRecord))


class SIAResultsErrorTest(unittest.TestCase):

    def testErrorVOTableInfo(self):
        resultfile = os.path.join(testdir, errresultfile)
        self.tbl = votableparse(resultfile)
        try:
            res = cs.CSResults(self.tbl)
            self.fail("Failed to detect error response")
        except dalq.DalQueryError, ex:
            self.assertEquals(ex.label, "Error")
            self.assertEquals(ex.reason, "Forced Fail")

    def testErrorResourceInfo(self):
        resultfile = os.path.join(testdir, "error3-cs.xml")
        self.tbl = votableparse(resultfile)
        try:
            res = cs.CSResults(self.tbl)
            self.fail("Failed to detect error response")
        except dalq.DalQueryError, ex:
            self.assertEquals(ex.label, "Error")
            self.assertEquals(ex.reason, "Forced Fail")

    def testErrorParam(self):
        resultfile = os.path.join(testdir, "error2-cs.xml")
        self.tbl = votableparse(resultfile)
        try:
            res = cs.CSResults(self.tbl)
            self.fail("Failed to detect error response")
        except dalq.DalQueryError, ex:
            self.assertEquals(ex.label, "Error")
            self.assertEquals(ex.reason, "DEC parameter out-of-range")

    def testErrorDefParam(self):
        resultfile = os.path.join(testdir, "error4-cs.xml")
        self.assertRaises(W22, votableparse, resultfile)


class CSRecordTest(unittest.TestCase):

    def setUp(self):
        resultfile = os.path.join(testdir, csresultfile)
        self.tbl = votableparse(resultfile)
        self.result = cs.CSResults(self.tbl)
        self.rec = self.result.getrecord(0)

    def testNameMap(self):
        self.assertEquals(self.rec._names["id"], "OBJID")
        self.assertEquals(self.rec._names["ra"], "RA")
        self.assertEquals(self.rec._names["dec"], "DEC")

    def testAttr(self):
        self.assertEquals(self.rec.ra, 0.065625)
        self.assertEquals(self.rec.dec, -8.8911667)
        self.assertEquals(self.rec.id, "34")

class CSExecuteTest(unittest.TestCase):
    baseurl = "http://localhost:%d/cs?"

    def testExecute(self):
        q = cs.CSQuery(self.baseurl % testserverport)
        q.ra = 0.0
        q.dec = 0.0
        q.sr = 0.25
        results = q.execute()
        self.assert_(isinstance(results, cs.CSResults))
        self.assertEquals(results.size, 2)

    def testSearch(self):
        srv = cs.CSService(self.baseurl % testserverport)
        results = srv.search(ra=0.0, dec=0.0, sr=0.25)
        self.assert_(isinstance(results, cs.CSResults))
        self.assertEquals(results.size, 2)

        qurl = results.queryurl
        # print qurl
        self.assert_("RA=0.0" in qurl)
        self.assert_("DEC=0.0" in qurl)
        self.assert_("SR=0.25" in qurl)
        self.assert_("VERB=2" in qurl)


    def testConesearch(self):
        # pdb.set_trace()
        results = cs.conesearch(self.baseurl % testserverport, 
                                ra=0.0, dec=0.0, sr=0.25)
        self.assert_(isinstance(results, cs.CSResults))
        self.assertEquals(results.size, 2)
        

__all__ = "CSServiceTest CSQueryTest CSResultsTest CSRecordTest CSExecuteTest".split()
def suite():
    tests = []
    for t in __all__:
        tests.append(unittest.makeSuite(globals()[t]))
    return unittest.TestSuite(tests)

if __name__ == "__main__":
    srvr = testserver.TestServer(testserverport)
    try:
        srvr.start()
        unittest.main()
    finally:
        if srvr.isAlive():
            srvr.shutdown()
