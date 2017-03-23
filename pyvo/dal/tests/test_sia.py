#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.dal.sia
"""
from __future__ import (
    absolute_import, division, print_function, unicode_literals)

import os, sys, shutil, re, imp, glob, tempfile, random, time
import unittest, pdb

import pyvo.dal.query as dalq
import pyvo.dal.sia as sia
import pyvo.dal.dbapi2 as daldbapi
# from astropy.io.vo import parse as votableparse
from astropy.io.votable.tree import VOTableFile
from astropy.io.votable import parse as votableparse
from astropy.utils.data import get_pkg_data_filename
from astropy.units import UnitConversionError
from . import testserver

siaresultfile = "data/neat-sia.xml"
errresultfile = "data/error-sia.xml"
testserverport = 8084
testserverport += 50
testserverport += random.randint(0,9)

class SIAServiceTest(unittest.TestCase):

    baseurl = "http://localhost/sia"

    def testCtor(self):
        self.srv = sia.SIAService(self.baseurl)

    def testProps(self):
        self.testCtor()
        self.assertEquals(self.srv.baseurl, self.baseurl)

    def testCreateQuery(self):
        self.testCtor()
        q = self.srv.create_query()
        self.assertIsInstance(q, sia.SIAQuery)
        self.assertEquals(q.baseurl, self.baseurl)
        self.assertEquals(len(q.keys()), 0)

    def testCreateQueryWithArgs(self):
        self.testCtor()
        q = self.srv.create_query(
            pos=(0, 0), size=(1.0, 1.0), format="all", intersect="overlaps",
            verbosity=2)
        self.assert_(isinstance(q, sia.SIAQuery))
        self.assertEquals(q.baseurl, self.baseurl)
        self.assertEquals(len(q.keys()), 5)

        self.assertEquals(q.pos, (0.0, 0.0))
        self.assertEquals(q.size, (1.0, 1.0))
        self.assertEquals(q.format, "all")
        self.assertEquals(q.intersect, "overlaps")
        self.assertEquals(q.verbosity, 2)

        self.assertEquals(q["POS"], "0.0,0.0")
        self.assertEquals(q["SIZE"], "1.0,1.0")
        self.assertEquals(q["FORMAT"], "ALL")
        self.assertEquals(q["INTERSECT"], "OVERLAPS")
        self.assertEquals(q["VERB"], 2)

    def testCreateQueryWithKws(self):
        self.testCtor()
        q = self.srv.create_query(CDELT=0.00028)
        self.assertAlmostEquals(0.00028, q["CDELT"])

        q.pos = (0, 0)
        q.size = (1.0, 1.0)
        self.assertEquals(q["POS"], "0.0,0.0")
        self.assertEquals(q["SIZE"], "1.0,1.0")

        q = self.srv.create_query(
            pos=(0, 0), size=(1.0, 1.0), format="all", intersect="overlaps",
            verbosity=2, CDELT=0.00028)
        self.assertIsInstance(q, sia.SIAQuery)
        self.assertEquals(q.baseurl, self.baseurl)
        self.assertEquals(len(q.keys()), 6)

        self.assertEquals(q.pos, (0.0, 0.0))
        self.assertEquals(q.size, (1.0, 1.0))
        self.assertEquals(q.format, "all")
        self.assertEquals(q.intersect, "overlaps")
        self.assertEquals(q.verbosity, 2)
        self.assertAlmostEquals(q['CDELT'], 0.00028)


class SIAQueryTest(unittest.TestCase):

    baseurl = "http://localhost/sia"

    def testCtor(self):
        self.q = sia.SIAQuery(self.baseurl)
        self.assertEquals(self.q.baseurl, self.baseurl)

    def testPos(self):
        self.testCtor()

        self.assert_(self.q.pos is None)

        self.q.pos = (180.2, -30.1)
        self.assertEquals(self.q.pos, (180.2, -30.1))

        self.q.pos = [170.2, -20.1]
        self.assertEquals(self.q.pos, [170.2, -20.1])

    def testBadPos(self):
        self.testCtor()
        try:
            self.q.pos = 22.3
            self.fail("pos took scalar value")
        except ValueError:
            pass

        try:
            self.q.pos = range(4)
            self.fail("pos took bad-length array value")
        except ValueError:
            pass

        try:
            self.q.pos = "a b".split()
            self.fail("pos took string values")
        except ValueError:
            pass

    def testSize(self):
        self.testCtor()
        self.assert_(self.q.size is None)

        self.q.size = (1.0, 2.0)
        self.assertEquals(len(self.q.size), 2)
        self.assertEquals(self.q.size, (1.0, 2.0))

        del self.q.size
        self.assert_(self.q.size is None)

        self.q.size = 0.5
        self.assertRaises(TypeError, len, self.q.size)
        self.assertEquals(self.q.size, 0.5)

        self.q.size = [1.0, 2.0]
        self.assertEquals(self.q.size, [1.0, 2.0])

    def testProps(self):
        self.testCtor()

        self.assertIsNone(self.q.verbosity)
        self.q.verbosity = 1
        self.assertEquals(self.q.verbosity, 1)
        del self.q.verbosity
        self.assertIsNone(self.q.verbosity)

        self.assertIsNone(self.q.intersect)
        self.q.intersect = "covers"
        self.assertEquals(self.q.intersect, "covers")
        del self.q.intersect
        self.assertIsNone(self.q.intersect)

    def testFormat(self):
        self.testCtor()

        self.assert_(self.q.format is None)
        self.q.format = "ALL"
        self.assertEquals(self.q.format, "ALL")
        del self.q.format
        self.assert_(self.q.format is None)

        self.q.format = "ALL"
        self.assertEquals(self.q.format, "ALL")

        #self.q.format = ["graphic-png", "jpeg", "gif"]
        #self.assertEquals(self.q.format, ["GRAPHIC-png", "jpeg", "gif"])

        self.q.format = "image/fits"
        self.assertEquals(self.q.format, "image/fits")

        self.q.format = ["image/fits"]
        self.assertEquals(self.q.format, ["image/fits"])

        self.q.format = ("image/fits",)
        self.assertEquals(self.q.format, ("image/fits",))

        self.q.format = {"image/fits"}
        self.assertEquals(self.q.format, {"image/fits"})

        self.q.format = ["image/fits", "text/html"]
        self.assertEquals(self.q.format, ["image/fits", "text/html"])
        self.assertEquals(len(self.q.format), 2)

        self.q.format = ("image/fits", "text/html")
        self.assertEquals(self.q.format, ("image/fits", "text/html"))
        self.assertEquals(len(self.q.format), 2)

        self.q.format = {"image/fits", "text/html"}
        self.assertEquals(self.q.format, {"image/fits", "text/html"})
        self.assertEquals(len(self.q.format), 2)

    def _assertPropSetRaises(self, extype, obj, att, val):
        try:
            setattr(obj, att, val)
            self.fail("Failed to raise ValueError for {0}={1}".format(
                att,str(val)))
        except extype:
            pass
        except Exception as ex:
            self.fail("Raised wrong exception: {0}: {1}".format(
                str(type(ex)), str(ex)))

    def testCreateURL(self):
        self.testCtor()
        qurl = self.q.queryurl
        self.assertEquals(qurl, self.baseurl)


class SIAResultsTest(unittest.TestCase):

    def setUp(self):
        resultfile = get_pkg_data_filename(siaresultfile)
        self.tbl = votableparse(resultfile)

    def testCtor(self):
        self.r = sia.SIAResults(self.tbl)
        self.assert_(isinstance(self.r._fldnames, list))
        self.assert_(self.r.votable is not None)
        self.assertEquals(len(self.r), 2)

    def testGetRecord(self):
        self.testCtor()
        rec = self.r.getrecord(0)
        self.assert_(isinstance(rec, sia.SIARecord))
        rec = self.r.getrecord(1)
        self.assert_(isinstance(rec, sia.SIARecord))

class SIAResultsErrorTest(unittest.TestCase):

    def setUp(self):
        resultfile = get_pkg_data_filename(errresultfile)
        self.tbl = votableparse(resultfile)

    def testError(self):
        try:
            res = sia.SIAResults(self.tbl)
            self.fail("Failed to detect error response")
        except dalq.DALQueryError as ex:
            self.assertEquals(ex.label, "ERROR")
            self.assertEquals(ex.reason, "Forced Fail")

class SIARecordTest(unittest.TestCase):

    acref = "http://skyview.gsfc.nasa.gov/cgi-bin/images?position=0.0%2C0.0&survey=neat&pixels=300%2C300&sampler=Clip&size=1.0%2C1.0&projection=Tan&coordinates=J2000.0&return=FITS"

    def setUp(self):
        resultfile = get_pkg_data_filename(siaresultfile)
        self.tbl = votableparse(resultfile)
        self.result = sia.SIAResults(self.tbl)
        self.rec = self.result.getrecord(0)


    def testAttr(self):
        self.assertEquals(self.rec.pos.ra.deg, 0.0)
        self.assertEquals(self.rec.pos.dec.deg, 0.0)
        self.assertEquals(self.rec.title, "neat")
        self.assert_(self.rec.dateobs is None)
        self.assertEquals(self.rec.naxes, 2)
        self.assertEquals(self.rec.naxis[0].value, 300)
        self.assertEquals(self.rec.naxis[1].value, 300)
        self.assert_(self.rec.instr is None)
        self.assertEquals(self.rec.acref, self.acref)
        self.assertEquals(self.rec.getdataurl(), self.acref)

class SIAExecuteTest(unittest.TestCase):

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
        q = sia.SIAQuery("http://localhost:{0}/sia".format(self.srvr.port))
        q.pos = (0, 0)
        q.size = (1.0, 1.0)
        q.format = "all"
        results = q.execute()
        self.assert_(isinstance(results, sia.SIAResults))
        self.assertEquals(len(results), 2)

    def testSearch(self):
        srv = sia.SIAService("http://localhost:{0}/sia".format(self.srvr.port))
        results = srv.search(pos=(0, 0), size=(1.0, 1.0))
        self.assert_(isinstance(results, sia.SIAResults))
        self.assertEquals(len(results), 2)

    def testSia(self):
        results = sia.search(
            "http://localhost:{0}/sia".format(self.srvr.port), pos=(0, 0),
            size=(1.0, 1.0))
        self.assertIsInstance(results, sia.SIAResults)
        self.assertEquals(len(results), 2)

    def testError(self):
        srv = sia.SIAService("http://localhost:{0}/err".format(self.srvr.port))
        self.assertRaises(dalq.DALQueryError, srv.search, (0.0, 0.0), 1.0)
        

class DatasetNameTest(unittest.TestCase):

    base = "testim"

    def setUp(self):
        resultfile = get_pkg_data_filename(siaresultfile)
        self.tbl = votableparse(resultfile)
        self.result = sia.SIAResults(self.tbl)
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
        title = self.rec.title
        self.assertEquals(title, self.rec.suggest_dataset_basename())
        self.assertEquals("fits", self.rec.suggest_extension("DAT"))

    def testMakeDatasetName(self):
        self.assertEquals("./neat.fits", self.rec.make_dataset_filename())
        self.assertEquals("./goober.fits", 
                          self.rec.make_dataset_filename(base="goober"))
        self.assertEquals("./neat.jpg", 
                          self.rec.make_dataset_filename(ext="jpg"))
        self.assertEquals("./goober.jpg", 
                          self.rec.make_dataset_filename(base="goober", 
                                                         ext="jpg"))
                          
        self.assertEquals(self.outdir+"/neat.fits", 
                          self.rec.make_dataset_filename(self.outdir))

        path = os.path.join(self.outdir,self.base+".fits")
        self.assertFalse(os.path.exists(path))
        self.assertEquals(path, 
                          self.rec.make_dataset_filename(self.outdir, self.base))
        open(path,'w').close()
        self.assertTrue(os.path.exists(path))
        path = os.path.join(self.outdir,self.base+"-1.fits")
        self.assertEquals(path, 
                          self.rec.make_dataset_filename(self.outdir, self.base))
        open(path,'w').close()
        self.assertTrue(os.path.exists(path))
        path = os.path.join(self.outdir,self.base+"-2.fits")
        self.assertEquals(path, 
                          self.rec.make_dataset_filename(self.outdir, self.base))
        open(path,'w').close()
        self.assertTrue(os.path.exists(path))
        path = os.path.join(self.outdir,self.base+"-3.fits")
        self.assertEquals(path, 
                          self.rec.make_dataset_filename(self.outdir, self.base))
                         
        self.cleanfiles()
        open(os.path.join(self.outdir,self.base+".fits"),'w').close()
        path = os.path.join(self.outdir,self.base+"-1.fits")
        self.assertEquals(path, 
                          self.rec.make_dataset_filename(self.outdir, self.base))
        open(os.path.join(self.outdir,self.base+"-1.fits"),'w').close()
        open(os.path.join(self.outdir,self.base+"-2.fits"),'w').close()
        open(os.path.join(self.outdir,self.base+"-3.fits"),'w').close()
        path = os.path.join(self.outdir,self.base+"-4.fits")
        self.assertEquals(path, 
                          self.rec.make_dataset_filename(self.outdir, self.base))

        self.cleanfiles()
        self.assertEquals(os.path.join(self.outdir,self.base+".fits"),
                          self.rec.make_dataset_filename(self.outdir, self.base))


__all__ = "SIAServiceTest SIAQueryTest SIAResultsTest SIARecordTest SIAExecuteTest DatasetNameTest".split()
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
