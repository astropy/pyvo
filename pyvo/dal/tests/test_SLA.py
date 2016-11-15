#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.dal.sla
"""
from __future__ import print_function, division

import os, sys, shutil, re, imp, random, time
import unittest, pdb

import pyvo.dal.query as dalq
import pyvo.dal.sla as sla
import pyvo.dal.dbapi2 as daldbapi
# from astropy.io.vo import parse as votableparse
from astropy.io.votable.tree import VOTableFile
from pyvo.dal.query import _votableparse as votableparse
from astropy.utils.data import get_pkg_data_filename
from . import aTestDALServer as testserve

slaresultfile = "data/nrao-sla.xml"
errresultfile = "data/error-sla.xml"
testserverport = 8084
testserverport += 30
testserverport += random.randint(0,9)

class SLAServiceTest(unittest.TestCase):

    baseurl = "http://localhost/sla"

    def testCtor(self):
        self.res = {"title": "Archive", "shortName": "arch"}
        self.srv = sla.SLAService(self.baseurl, resmeta=self.res)

    def testProps(self):
        self.testCtor()
        self.assertEquals(self.srv.baseurl, self.baseurl)
        self.assertEquals(self.srv.protocol, "sla")
        self.assertEquals(self.srv.version, "1.0")
        try:
            self.srv.baseurl = "goober"
            self.fail("baseurl not read-only")
        except AttributeError:
            pass

        self.assertEquals(self.srv.info["title"], "Archive")
        self.assertEquals(self.srv.info["shortName"], "arch")
        self.srv.info["title"] = "Sir"
        self.assertEquals(self.res["title"], "Archive")

    def testCreateQuery(self):
        self.testCtor()
        q = self.srv.create_query()
        self.assert_(isinstance(q, sla.SLAQuery))
        self.assertEquals(q.baseurl, self.baseurl)
        self.assertEquals(len(q.keys()), 1)

    def testCreateQueryWithArgs(self):
        self.testCtor()
        q = self.srv.create_query(wavelength="7.6e-6/1.e-5")
        self.assert_(isinstance(q, sla.SLAQuery))
        self.assertEquals(q.baseurl, self.baseurl)
        self.assertEquals(len(q.keys()), 2)

        self.assertEquals(q.wavelength, "7.6e-6/1.e-5")

        qurl = q.getqueryurl()
        self.assertEquals(q["REQUEST"], "queryData")
        self.assertEquals(q["WAVELENGTH"], "7.6e-6/1.e-5")
        

class SLAQueryTest(unittest.TestCase):

    baseurl = "http://localhost/sla"

    def testCtor(self):
        self.q = sla.SLAQuery(self.baseurl)
        self.assertEquals(self.q.baseurl, self.baseurl)
        self.assertEquals(self.q.protocol, "sla")
        self.assertEquals(self.q.version, "1.0")

    def testWavelength(self):
        self.testCtor()
        self.assert_(self.q.wavelength is None)

        self.q.wavelength = "7.6e-6/1.e-5"
        self.assertEquals(self.q.wavelength, "7.6e-6/1.e-5")

        del self.q.wavelength
        self.assert_(self.q.wavelength is None)

        self.q.wavelength = "7.6e-6/1.e-5"
        self.assertEquals(self.q.wavelength, "7.6e-6/1.e-5")

    def testBadWavelength(self):
        self.testCtor()
        try:
            self.q.wavelength = "7.6e-6,"; self.fail("incorrect syntax for wavelength")
        except ValueError:  pass

        try:
            self.q.wavelength = "7.6e-6//1.e-5"; self.fail("incorrect syntax for wavelength")
        except ValueError:  pass

        try:
            self.q.wavelength = "7.6e-6/1.e-5/"; self.fail("incorrect syntax for wavelength")
        except ValueError:  pass

            

    def testCreateURL(self):
        self.testCtor()
        self.q.wavelength = "7.6e-6/1.e-5"
        qurl = self.q.getqueryurl()
        self.assertEquals(qurl, self.baseurl)


class SLAResultsTest(unittest.TestCase):

    def setUp(self):
        resultfile = get_pkg_data_filename(slaresultfile)
        self.tbl = votableparse(resultfile)

    def testCtor(self):
        self.r = sla.SLAResults(self.tbl)
        self.assertEquals(self.r.protocol, "sla")
        self.assertEquals(self.r.version, "1.0")
        self.assert_(isinstance(self.r._fldnames, list))
        self.assert_(self.r.votable is not None)
        self.assertEquals(self.r.nrecs, 21)

    def testUTypeMap(self):
        self.testCtor()
        self.assertEquals(self.r._slacols["ssldm:Line.title"], "title")

        self.assertEquals(self.r._recnames["title"], "title")

    def testGetRecord(self):
        self.testCtor()
        rec = self.r.getrecord(0)
        self.assert_(isinstance(rec, sla.SLARecord))
        rec = self.r.getrecord(1)
        self.assert_(isinstance(rec, sla.SLARecord))

class SLAResultsErrorTest(unittest.TestCase):

    def setUp(self):
        resultfile = get_pkg_data_filename(errresultfile)
        self.tbl = votableparse(resultfile)

    def testError(self):
        try:
            res = sla.SLAResults(self.tbl)
            self.fail("Failed to detect error response")
        except dalq.DALQueryError as ex:
            self.assertEquals(ex.label, "ERROR")
            self.assertEquals(ex.reason, "Forced Fail")

class SLARecordTest(unittest.TestCase):

    def setUp(self):
        resultfile = get_pkg_data_filename(slaresultfile)
        self.tbl = votableparse(resultfile)
        self.result = sla.SLAResults(self.tbl)
        self.rec = self.result.getrecord(0)

    def testNameMap(self):
        self.assertEquals(self.rec._names["title"], "title")

    def testAttr(self):
        self.assertEquals(self.rec.title, b"JPL: CH2OHCOCH2OH v29=1 65(10,55)-65( 9,56)")
        self.assertAlmostEquals(self.rec.wavelength, 0.0026007993198247656)
        self.assertEquals(self.rec.species_name, b"Dihydroxyacetone")
        self.assertTrue(self.rec.status is None)
        self.assertTrue(self.rec.initial_level is None)
        self.assertTrue(self.rec.final_level is None)

class SLAExecuteTest(unittest.TestCase):

    srvr = None

    @classmethod
    def setup_class(cls):
        cls.srvr = testserve.get_server(testserverport)
        cls.srvr.start()
        time.sleep(0.5)

    @classmethod
    def teardown_class(cls):
        if cls.srvr.is_alive():
            cls.srvr.terminate()
        if cls.srvr.is_alive():
            print("prob")

    def testExecute(self):
        q = sla.SLAQuery("http://localhost:{0}/sla".format(self.srvr.port))
        q.wavelength = "0.00260075/0.00260080"
        results = q.execute()
        self.assert_(isinstance(results, sla.SLAResults))
        self.assertEquals(results.nrecs, 21)

    def testSearch(self):
        srv = sla.SLAService("http://localhost:{0}/sla".format(self.srvr.port))
        results = srv.search(wavelength="0.00260075/0.00260080")
        self.assert_(isinstance(results, sla.SLAResults))
        self.assertEquals(results.nrecs, 21)

    def testSla(self):
        results = sla.search("http://localhost:{0}/sla".format(self.srvr.port),
                             wavelength="0.00260075/0.00260080")
        self.assert_(isinstance(results, sla.SLAResults))
        self.assertEquals(results.nrecs, 21)

    def testError(self):
        srv = sla.SLAService("http://localhost:{0}/err".format(self.srvr.port))
        self.assertRaises(dalq.DALQueryError, srv.search, "0.00260075/0.00260080")
        

__all__ = "SLAServiceTest SLAQueryTest SLAResultsTest SLARecordTest SLAExecuteTest".split()
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

    srvr = testserve.TestServer(testserverport)

    try:
        srvr.start()
        unittest.main()
    finally:
        if srvr.is_alive():
            srvr.terminate()
