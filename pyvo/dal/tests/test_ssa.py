#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.dal.ssa
"""
from __future__ import (
    absolute_import, division, print_function, unicode_literals)

import os, sys, shutil, re, imp, glob, tempfile, random, time
import unittest, pdb

import pyvo.dal.query as dalq
import pyvo.dal.ssa as ssa
import pyvo.dal.dbapi2 as daldbapi
from astropy.time import Time
# from astropy.io.vo import parse as votableparse
from astropy.io.votable.tree import VOTableFile
from astropy.io.votable import parse as votableparse
from astropy.utils.data import get_pkg_data_filename
from . import testserver

testdir = os.path.dirname(sys.argv[0])
if not testdir:  testdir = "tests"
ssaresultfile = "data/jhu-ssa.xml"
errresultfile = "data/error-ssa.xml"
testserverport = 8084
testserverport += 40
testserverport += random.randint(0,9)

class SSAServiceTest(unittest.TestCase):

    baseurl = "http://localhost/ssa"

    def testCtor(self):
        self.srv = ssa.SSAService(self.baseurl)

    def testProps(self):
        self.testCtor()
        self.assertEquals(self.srv.baseurl, self.baseurl)
        try:
            self.srv.baseurl = "goober"
            self.fail("baseurl not read-only")
        except AttributeError:
            pass

    def testCreateQuery(self):
        self.testCtor()
        q = self.srv.create_query()
        self.assert_(isinstance(q, ssa.SSAQuery))
        self.assertEquals(q.baseurl, self.baseurl)
        self.assertEquals(len(q.keys()), 1)

    def testCreateQueryWithArgs(self):
        self.testCtor()
        q = self.srv.create_query(pos=(0.0, 0.0), diameter=1.0, format="all")
        self.assert_(isinstance(q, ssa.SSAQuery))
        self.assertEquals(q.baseurl, self.baseurl)
        self.assertEquals(len(q.keys()), 4)

        self.assertEquals(q.pos, (0.0, 0.0))
        self.assertEquals(q.diameter, 1.0)
        self.assertEquals(q.format, "all")

        self.assertEquals(q["REQUEST"], "queryData")
        self.assertAlmostEquals(q["POS"], "0.0,0.0")
        self.assertAlmostEquals(q["SIZE"], 1.0)
        self.assertEquals(q["FORMAT"], "all")

    def testCreateQueryWithKws(self):
        self.testCtor()
        q = self.srv.create_query(APERTURE=0.00028)
        self.assertAlmostEquals(0.00028, q["APERTURE"])

        q.pos = (0.0, 0.0)
        q.diameter = 1.0
        self.assertEquals(q.pos, (0.0, 0.0))
        self.assertEquals(q.diameter, 1.0)
        self.assertEquals(len(q.keys()), 4)
        self.assertAlmostEquals(q['APERTURE'], 0.00028)
        self.assertEquals(q["REQUEST"], "queryData")
        self.assertAlmostEquals(q["POS"], "0.0,0.0")
        self.assertAlmostEquals(q["SIZE"], 1.0)

        q = self.srv.create_query(
            pos=(0.0, 0.0), diameter=1.0, format="all", APERTURE=0.00028)
        self.assert_(isinstance(q, ssa.SSAQuery))
        self.assertEquals(q.baseurl, self.baseurl)
        self.assertEquals(len(q.keys()), 5)

        self.assertEquals(q.pos, (0,0))
        self.assertEquals(q.diameter, 1.0)
        self.assertEquals(q.format, "all")
        self.assertAlmostEquals(q['APERTURE'], 0.00028)

        self.assertEquals(q["REQUEST"], "queryData")
        self.assertAlmostEquals(q["POS"], "0.0,0.0")
        self.assertAlmostEquals(q["SIZE"], 1.0)
        self.assertEquals(q["FORMAT"], "all")


class SSAQueryTest(unittest.TestCase):

    baseurl = "http://localhost/ssa"

    def testCtor(self):
        self.q = ssa.SSAQuery(self.baseurl)
        self.assertEquals(self.q.baseurl, self.baseurl)

    def testPos(self):
        self.testCtor()
        self.assertIsNone(self.q.pos)

        self.q.pos = (120.445, 30.0)
        self.assertEquals(self.q.pos, (120.445, 30.0))

        del self.q.pos
        self.assert_(self.q.pos is None)

        self.q.pos = (180.2, -30.1)
        self.assertEquals(self.q.pos, (180.2, -30.1))

        self.q.pos = [170.2, -20.1]
        self.assertEquals(self.q.pos, [170.2, -20.1])

    def testSize(self):
        self.testCtor()
        self.assert_(self.q.diameter is None)

        self.q.diameter = 1.5
        self.assertEquals(self.q.diameter, 1.5)

        del self.q.diameter
        self.assert_(self.q.diameter is None)

        self.q.diameter = 0.5
        self.assertEquals(self.q.diameter, 0.5)

    def testProps(self):
        self.testCtor()
        self.assert_(self.q.format is None)
        self.q.format = "all"
        self.assertEquals(self.q.format, "all")
        del self.q.format
        self.assert_(self.q.format is None)

    def testFormat(self):
        self.testCtor()
        self.assert_(self.q.format is None)
        self.q.format = "all"
        self.assertEquals(self.q.format, "all")
        del self.q.format
        self.assert_(self.q.format is None)

        # check all special values
        for val in "compliant native graphic votable fits xml metadata".split():
            self.q.format = val
            self.assertEquals(self.q.format, val)

        # make sure MIME-type value is accepted
        self.q.format = "image/jpeg"
        self.assertEquals(self.q.format, "image/jpeg")

        # check for list values
        self.q.format = "fits,image/jpeg"

    def testCreateURL(self):
        self.testCtor()
        self.q.pos = (102.5511, 24.312)
        qurl = self.q.queryurl
        self.assertEquals(qurl, self.baseurl)

        self.q.diameter = 1.0
        qurl = self.q.queryurl
        self.assertAlmostEquals(self.q["POS"], "102.5511,24.312")
        self.assertAlmostEquals(self.q["SIZE"], 1.0)


class SSAResultsTest(unittest.TestCase):

    def setUp(self):
        resultfile = get_pkg_data_filename(ssaresultfile)
        self.tbl = votableparse(resultfile)

    def testCtor(self):
        self.r = ssa.SSAResults(self.tbl)
        self.assertIsInstance(self.r._fldnames, list)
        self.assertIsNotNone(self.r.votable)
        self.assertEquals(len(self.r), 35)

    def testGetRecord(self):
        self.testCtor()
        rec = self.r.getrecord(0)
        self.assertIsInstance(rec, ssa.SSARecord)
        rec = self.r.getrecord(1)
        self.assertIsInstance(rec, ssa.SSARecord)

class SSAResultsErrorTest(unittest.TestCase):

    def setUp(self):
        resultfile = get_pkg_data_filename(errresultfile)
        self.tbl = votableparse(resultfile)

    def testError(self):
        try:
            res = ssa.SSAResults(self.tbl)
            self.fail("Failed to detect error response")
        except dalq.DALQueryError as ex:
            self.assertEquals(ex.label, "ERROR")
            self.assertEquals(ex.reason, "Forced Fail")

class SSARecordTest(unittest.TestCase):

    acref = "http://vaosa-vm1.aoc.nrao.edu/ivoa-dal/JhuSsapServlet?REQUEST=getData&FORMAT=votable&PubDID=ivo%3A%2F%2Fjhu%2Fsdss%2Fdr6%2Fspec%2F2.5%2380442261170552832"

    def setUp(self):
        resultfile = get_pkg_data_filename(ssaresultfile)
        self.tbl = votableparse(resultfile)
        self.result = ssa.SSAResults(self.tbl)
        self.rec = self.result.getrecord(0)

    def testAttr(self):
        self.assertEquals(self.rec.ra, 179.84916)
        self.assertEquals(self.rec.dec, 0.984768)
        self.assertEquals(self.rec.title, "SDSS J115923.80+005905.16 GALAXY")
        self.assertEquals(
            self.rec.dateobs, Time("2000-04-29 03:22:00Z", format="iso"))
        self.assertEquals(self.rec.instr, "SDSS 2.5-M SPEC2 v4_5")
        self.assertEquals(self.rec.acref, self.acref)
        self.assertEquals(self.rec.getdataurl(), self.acref)

class SSAExecuteTest(unittest.TestCase):

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
        q = ssa.SSAQuery("http://localhost:{0}/ssa".format(self.srvr.port))
        q.pos = (0, 0)
        q.diameter = 1.0
        q.format = "all"
        results = q.execute()
        self.assertIsInstance(results, ssa.SSAResults)
        self.assertEquals(len(results), 35)

    def testSearch(self):
        srv = ssa.SSAService("http://localhost:{0}/ssa".format(self.srvr.port))
        results = srv.search(pos=(0.0, 0.0), diameter=1.0)
        self.assertIsInstance(results, ssa.SSAResults)
        self.assertEquals(len(results), 35)


    def testSsa(self):
        results = ssa.search(
            "http://localhost:{0}/ssa".format(self.srvr.port), pos=(0.0, 0.0),
            diameter=1.0)
        self.assertIsInstance(results, ssa.SSAResults)
        self.assertEquals(len(results), 35)

    def testError(self):
        srv = ssa.SSAService("http://localhost:{0}/err".format(self.srvr.port))
        self.assertRaises(dalq.DALQueryError, srv.search, (0.0, 0.0), 1.0)


class DatasetNameTest(unittest.TestCase):

    base = "testspec"

    def setUp(self):
        resultfile = get_pkg_data_filename(ssaresultfile)
        self.tbl = votableparse(resultfile)
        self.result = ssa.SSAResults(self.tbl)
        self.rec = self.result.getrecord(0)

        self.outdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.outdir)

    def cleanfiles(self, tmpdir=None):
        if not tmpdir:
            tmpdir = self.outdir
        if not os.path.isdir(tmpdir):
            return
        files = glob.glob(os.path.join(tmpdir, self.base+"*.*"))
        for f in files:
            os.remove(f)

    def testSuggest(self):
        self.assertEquals("SDSS_J115923.80+005905.16_GALAXY", 
                          self.rec.suggest_dataset_basename())
        self.assertEquals("xml", self.rec.suggest_extension("DAT"))

    def testMakeDatasetName(self):
        self.assertTrue(os.path.isdir(self.outdir))
        self.assertEquals("./SDSS_J115923.80+005905.16_GALAXY.xml", 
                          self.rec.make_dataset_filename())
        self.assertEquals("./goober.xml", 
                          self.rec.make_dataset_filename(base="goober"))
        self.assertEquals("./SDSS_J115923.80+005905.16_GALAXY.jpg", 
                          self.rec.make_dataset_filename(ext="jpg"))
        self.assertEquals("./goober.jpg", 
                          self.rec.make_dataset_filename(base="goober", 
                                                         ext="jpg"))
                          
        self.assertEquals(self.outdir+"/SDSS_J115923.80+005905.16_GALAXY.xml", 
                          self.rec.make_dataset_filename(self.outdir))

        path = os.path.join(self.outdir,self.base+".xml")
        self.assertFalse(os.path.exists(path))
        self.assertEquals(path, 
                          self.rec.make_dataset_filename(self.outdir, self.base))
        open(path,'w').close()
        self.assertTrue(os.path.exists(path))
        path = os.path.join(self.outdir,self.base+"-1.xml")
        self.assertEquals(path, 
                          self.rec.make_dataset_filename(self.outdir, self.base))
        open(path,'w').close()
        self.assertTrue(os.path.exists(path))
        path = os.path.join(self.outdir,self.base+"-2.xml")
        self.assertEquals(path, 
                          self.rec.make_dataset_filename(self.outdir, self.base))
        open(path,'w').close()
        self.assertTrue(os.path.exists(path))
        path = os.path.join(self.outdir,self.base+"-3.xml")
        self.assertEquals(path, 
                          self.rec.make_dataset_filename(self.outdir, self.base))
                         
        self.cleanfiles()
        open(os.path.join(self.outdir,self.base+".xml"),'w').close()
        path = os.path.join(self.outdir,self.base+"-1.xml")
        self.assertEquals(path, 
                          self.rec.make_dataset_filename(self.outdir, self.base))
        open(os.path.join(self.outdir,self.base+"-1.xml"),'w').close()
        open(os.path.join(self.outdir,self.base+"-2.xml"),'w').close()
        open(os.path.join(self.outdir,self.base+"-3.xml"),'w').close()
        path = os.path.join(self.outdir,self.base+"-4.xml")
        self.assertEquals(path, 
                          self.rec.make_dataset_filename(self.outdir, self.base))

        self.cleanfiles()
        self.assertEquals(os.path.join(self.outdir,self.base+".xml"),
                          self.rec.make_dataset_filename(self.outdir, self.base))



__all__ = "SSAServiceTest SSAQueryTest SSAResultsTest SSARecordTest SSAExecuteTest DatasetNameTest".split()
def suite():
    tests = []
    for t in __all__:
        tests.append(unittest.makeSuite(globals()[t]))
    return unittest.TestSuite(tests)

if __name__ == "__main__":
    try:
        module = find_current_module(1, True)
        pkgdir = os.path.dirname(module.__file__)
        t = "aTestDALServer"
        mod = imp.find_module(t, [pkgdir])
        testserve = imp.load_module(t, mod[0], mod[1], mod[2])
    except ImportError as e:
        sys.stderr.write("Can't find test server: aTestDALServer.py:"+str(e))

    srvr = testserver.TestServer(testserverport)

    try:
        srvr.start()
        unittest.main()
    finally:
        if srvr.is_alive():
            srvr.terminate()
