#!/usr/bin/env python
"""
Tests for vaopy.dal.query
"""
import os, sys, shutil, re, imp
import unittest, pdb
from urllib2 import URLError, HTTPError

import vaopy.dal.query as dalq
import vaopy.dal.sia as sia
import vaopy.dal.dbapi2 as daldbapi
# from astropy.io.vo import parse as votableparse
from astropy.io.votable.tree import VOTableFile
from vaopy.dal.query import _votableparse as votableparse

testdir = os.path.dirname(sys.argv[0])
if not testdir:  testdir = "tests"
siaresultfile = "neat-sia.xml"
errresultfile = "error-sia.xml"
testserverport = 8081

try:
    t = "aTestSIAServer"
    mod = imp.find_module(t, [testdir])
    testserver = imp.load_module(t, mod[0], mod[1], mod[2])
    testserver.testdir = testdir
except ImportError, e:
    print >> sys.stderr, "Can't find test server: aTestSIAServer.py:", str(e)

class SIAServiceTest(unittest.TestCase):

    baseurl = "http://localhost/sia"

    def testCtor(self):
        self.res = {"title": "Archive", "shortName": "arch"}
        self.srv = sia.SIAService(self.baseurl, resmeta=self.res)

    def testProps(self):
        self.testCtor()
        self.assertEquals(self.srv.baseurl, self.baseurl)
        self.assertEquals(self.srv.protocol, "sia")
        self.assertEquals(self.srv.version, "1.0")
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
        q = self.srv.create_query()
        self.assert_(isinstance(q, sia.SIAQuery))
        self.assertEquals(q.baseurl, self.baseurl)
        self.assertEquals(len(q._param.keys()), 0)

    def testCreateQueryWithArgs(self):
        self.testCtor()
        q = self.srv.create_query(pos=(0,0), size=(1.0,1.0), format="all", 
                                  intersect="overlaps", verbosity=2)
        self.assert_(isinstance(q, sia.SIAQuery))
        self.assertEquals(q.baseurl, self.baseurl)
        self.assertEquals(len(q._param.keys()), 5)

        self.assertEquals(q.pos, (0,0))
        self.assertEquals(q.size, (1.0,1.0))
        self.assertEquals(q.format, "ALL")
        self.assertEquals(q.intersect, "OVERLAPS")
        self.assertEquals(q.verbosity, 2)

        qurl = q.getqueryurl()
        self.assert_("POS=0,0" in qurl)
        self.assert_("SIZE=1.0,1.0" in qurl)
        self.assert_("FORMAT=ALL" in qurl)
        self.assert_("INTERSECT=OVERLAPS" in qurl)
        self.assert_("VERB=2" in qurl)


class SIAQueryTest(unittest.TestCase):

    baseurl = "http://localhost/sia"

    def testCtor(self):
        self.q = sia.SIAQuery(self.baseurl)
        self.assertEquals(self.q.baseurl, self.baseurl)
        self.assertEquals(self.q.protocol, "sia")
        self.assertEquals(self.q.version, "1.0")

    def testPos(self):
        self.testCtor()
        self.assert_(self.q.pos is None)
        self.assert_(self.q.ra is None)
        self.assert_(self.q.dec is None)

        self.q.ra = 120.445
        self.assertEquals(self.q.ra, 120.445)
        self.assertEquals(self.q.dec, 0)
        self.assertEquals(self.q.pos, (120.445, 0))

        del self.q.pos
        self.assert_(self.q.pos is None)
        self.assert_(self.q.ra is None)
        self.assert_(self.q.dec is None)

        self.q.dec = 40.1434
        self.assertEquals(self.q.dec, 40.1434)
        self.assertEquals(self.q.ra, 0)
        self.assertEquals(self.q.pos, (0, 40.1434))

        self.q.pos = (180.2, -30.1)
        self.assertEquals(self.q.ra, 180.2)
        self.assertEquals(self.q.dec, -30.1)
        self.assertEquals(self.q.pos, (180.2, -30.1))

        self.q.pos = [170.2, -20.1]
        self.assertEquals(self.q.ra, 170.2)
        self.assertEquals(self.q.dec, -20.1)
        self.assertEquals(self.q.pos, (170.2, -20.1))

        self.q.ra = -45
        self.assertEquals(self.q.ra, 315)
        self.q.ra = 400
        self.assertEquals(self.q.ra, 40)

    def testBadPos(self):
        self.testCtor()
        try:
            self.q.pos = 22.3; self.fail("pos took scalar value")
        except ValueError:  pass
        try:
            self.q.pos = range(4); self.fail("pos took bad-length array value")
        except ValueError:  pass
        try:
            self.q.pos = "a b".split(); self.fail("pos took string values")
        except ValueError:  pass
        try:
            self.q.ra = "a b"; self.fail("ra took string values")
        except ValueError:  pass
        try:
            self.q.dec = "a b"; self.fail("dec took string values")
        except ValueError:  pass
        try:
            self.q.dec = 100; self.fail("dec took out-of-range value")
        except ValueError, e:  pass
            
            
    def testSize(self):
        self.testCtor()
        self.assert_(self.q.size is None)

        self.q.size = (1.0, 2.0)
        self.assertEquals(self.q.size[0], 1.0)
        self.assertEquals(self.q.size[1], 2.0)

        del self.q.size
        self.assert_(self.q.size is None)

        self.q.size = 0.5
        self.assertEquals(self.q.size[0], 0.5)
        self.assertEquals(self.q.size[1], 0.5)

        self.q.size = [1.0, 2.0]
        self.assertEquals(self.q.size[0], 1.0)
        self.assertEquals(self.q.size[1], 2.0)

    def testBadSize(self):
        self.testCtor()
        try: self.q.size[0] = 1.0; self.fail("updated size element")
        except TypeError: pass

        self.q.size = 1.0
        try: self.q.size[0] = 1.0; self.fail("updated size element")
        except TypeError: pass

        try:  self.q.size = range(4); self.fail("size took bad array")
        except ValueError: pass

        try:  self.q.size = "a b".split(); self.fail("size took non-numbers")
        except ValueError: pass

        try:  self.q.size = "a b"; self.fail("size took non-numbers")
        except ValueError: pass

        try:  self.q.size = [0.5, 200]; self.fail("size took out-of-range dec")
        except ValueError: pass

        try:  self.q.size = [500, 0.5]; self.fail("size took out-of-range ra")
        except ValueError: pass

        try:  self.q.size = [0.5, 0]; self.fail("size took out-of-range dec")
        except ValueError: pass

        try:  self.q.size = [0, 0.5]; self.fail("size took out-of-range ra")
        except ValueError: pass

        try:  self.q.size = [0.5, -5]; self.fail("size took out-of-range dec")
        except ValueError: pass

        try:  self.q.size = [-5, 0.5]; self.fail("size took out-of-range ra")
        except ValueError: pass

    def testProps(self):
        self.testCtor()
        self.assert_(self.q.format is None)
        self.q.format = "ALL"
        self.assertEquals(self.q.format, "ALL")
        del self.q.format
        self.assert_(self.q.format is None)

        self.assert_(self.q.verbosity is None)
        self.q.verbosity = 1
        self.assertEquals(self.q.verbosity, 1)
        del self.q.verbosity
        self.assert_(self.q.verbosity is None)
        try: self.q.verbosity = "ALL"; self.fail("verb set to non-int")
        except ValueError:  pass

        self.assert_(self.q.intersect is None)
        for val in "covers enclosed center overlaps".split() + "COVERS ENCLOSED CENTER OVERLAPS".split():
            self.q.intersect = val
            self.assertEquals(self.q.intersect, val.upper())

        del self.q.intersect
        self.assert_(self.q.intersect is None)
        try: self.q.intersect = "ALL"; self.fail("bad intersect value accepted")
        except ValueError:  pass

    def testCreateURL(self):
        self.testCtor()
        self.q.ra = 102.5511
        self.q.dec = 24.312
        qurl = self.q.getqueryurl()
        self.assertEquals(qurl, self.baseurl+"?POS=102.5511,24.312")

        self.q.size = (1.0, 1.0)
        qurl = self.q.getqueryurl()
        self.assert_("POS=102.5511,24.312" in qurl)
        self.assert_("SIZE=1.0,1.0" in qurl)


class SIAResultsTest(unittest.TestCase):

    def setUp(self):
        resultfile = os.path.join(testdir, siaresultfile)
        self.tbl = votableparse(resultfile)

    def testCtor(self):
        self.r = sia.SIAResults(self.tbl)
        self.assertEquals(self.r.protocol, "sia")
        self.assertEquals(self.r.version, "1.0")
        self.assert_(isinstance(self.r._fldnames, list))
        self.assert_(self.r._tbl is not None)
        self.assertEquals(self.r.rowcount, 2)

    def testUCDMap(self):
        self.testCtor()
        self.assertEquals(self.r._siacols["VOX:Image_Title"], "Survey")
        self.assertEquals(self.r._siacols["POS_EQ_RA_MAIN"], "Ra")
        self.assertEquals(self.r._siacols["VOX:Image_AccessReference"], "URL")
        self.assert_(self.r._siacols["VOX:Image_AccessRefTTL"] is None)

        self.assertEquals(self.r._recnames["title"], "Survey")
        self.assertEquals(self.r._recnames["ra"], "Ra")
        self.assertEquals(self.r._recnames["acref"], "URL")
        self.assert_(self.r._recnames["dateobs"] is None)

    def testGetRecord(self):
        self.testCtor()
        rec = self.r.getrecord(0)
        self.assert_(isinstance(rec, sia.SIARecord))
        rec = self.r.getrecord(1)
        self.assert_(isinstance(rec, sia.SIARecord))

class SIAResultsErrorTest(unittest.TestCase):

    def setUp(self):
        resultfile = os.path.join(testdir, errresultfile)
        self.tbl = votableparse(resultfile)

    def testError(self):
        try:
            res = sia.SIAResults(self.tbl)
            self.fail("Failed to detect error response")
        except dalq.DalQueryError, ex:
            self.assertEquals(ex.label, "ERROR")
            self.assertEquals(ex.reason, "Forced Fail")

class SIARecordTest(unittest.TestCase):

    acref = "http://skyview.gsfc.nasa.gov/cgi-bin/images?position=0.0%2C0.0&survey=neat&pixels=300%2C300&sampler=Clip&size=1.0%2C1.0&projection=Tan&coordinates=J2000.0&return=FITS"

    def setUp(self):
        resultfile = os.path.join(testdir, siaresultfile)
        self.tbl = votableparse(resultfile)
        self.result = sia.SIAResults(self.tbl)
        self.rec = self.result.getrecord(0)

    def testNameMap(self):
        self.assertEquals(self.rec._names["title"], "Survey")
        self.assertEquals(self.rec._names["ra"], "Ra")
        self.assertEquals(self.rec._names["acref"], "URL")
        self.assertEquals(self.rec._names["naxes"], "Dim")
        self.assertEquals(self.rec._names["naxis"], "Size")
        self.assert_(self.rec._names["dateobs"] is None)

    def testAttr(self):
        self.assertEquals(self.rec.ra, 0.0)
        self.assertEquals(self.rec.dec, 0.0)
        self.assertEquals(self.rec.title, "neat")
        self.assert_(self.rec.dateobs is None)
        self.assertEquals(self.rec.naxes, 2)
        self.assertEquals(self.rec.naxis, (300, 300))
        self.assert_(self.rec.instr is None)
        self.assertEquals(self.rec.acref, self.acref)
        self.assertEquals(self.rec.getdataurl(), self.acref)

class SIAExecuteTest(unittest.TestCase):

    def testExecute(self):
        q = sia.SIAQuery("http://localhost:%d/sia" % testserverport)
        q.pos = (0, 0)
        q.size = (1.0, 1.0)
        q.format = "all"
        results = q.execute()
        self.assert_(isinstance(results, sia.SIAResults))
        self.assertEquals(results.rowcount, 2)

    def testSearch(self):
        srv = sia.SIAService("http://localhost:%d/sia" % testserverport)
        results = srv.search(pos=(0,0), size=(1.0,1.0))
        self.assert_(isinstance(results, sia.SIAResults))
        self.assertEquals(results.rowcount, 2)

        qurl = results.queryurl
        # print qurl
        self.assert_("POS=0,0" in qurl)
        self.assert_("SIZE=1.0,1.0" in qurl)
        self.assert_("FORMAT=ALL" in qurl)
        self.assert_("INTERSECT=OVERLAPS" in qurl)
        self.assert_("VERB=2" in qurl)


    def testSia(self):
        results = sia.sia("http://localhost:%d/sia" % testserverport,
                          pos=(0,0), size=(1.0,1.0))
        self.assert_(isinstance(results, sia.SIAResults))
        self.assertEquals(results.rowcount, 2)

    def testError(self):
        srv = sia.SIAService("http://localhost:%d/err" % testserverport)
        self.assertRaises(dalq.DalQueryError, srv.search, (0.0,0.0), 1.0)
        

__all__ = "SIAServiceTest SIAQueryTest SIAResultsTest SIARecordTest SIAExecuteTest".split()
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
