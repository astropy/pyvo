#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.dal.sla
"""
from __future__ import print_function, division

import os, sys, shutil, re, imp
import unittest, pdb
from urllib2 import URLError, HTTPError

import pyvo.dal.query as dalq
import pyvo.dal.sla as sla
import pyvo.dal.dbapi2 as daldbapi
# from astropy.io.vo import parse as votableparse
from astropy.io.votable.tree import VOTableFile
from pyvo.dal.query import _votableparse as votableparse
from astropy.utils.data import get_pkg_data_filename
from . import aTestSIAServer as testserve

slaresultfile = "data/nrao-sla.xml"
errresultfile = "data/error-sla.xml"
testserverport = 8084
testserverport += 3

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

        self.assertEquals(self.srv.description["title"], "Archive")
        self.assertEquals(self.srv.description["shortName"], "arch")
        self.srv.description["title"] = "Sir"
        self.assertEquals(self.res["title"], "Archive")

    def testCreateQuery(self):
        self.testCtor()
        q = self.srv.create_query()
        self.assert_(isinstance(q, sla.SLAQuery))
        self.assertEquals(q.baseurl, self.baseurl)
        self.assertEquals(len(q._param.keys()), 1)

    def testCreateQueryWithArgs(self):
        self.testCtor()
        q = self.srv.create_query(wavelength="7.6e-6/1.e-5")
        self.assert_(isinstance(q, sla.SLAQuery))
        self.assertEquals(q.baseurl, self.baseurl)
        self.assertEquals(len(q._param.keys()), 2)

        self.assertEquals(q.wavelength, "7.6e-6/1.e-5")

        qurl = q.getqueryurl()
        self.assert_("REQUEST=queryData" in qurl)
        self.assert_("WAVELENGTH=7.6e-6%2F1.e-5" in qurl)
        

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
        self.assertEquals(qurl, self.baseurl+"?REQUEST=queryData&WAVELENGTH=7.6e-6%2F1.e-5")


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
        cls.srvr = testserve.TestServer(testserverport)
        cls.srvr.start()

    @classmethod
    def teardown_class(cls):
        if cls.srvr.isAlive():
            cls.srvr.shutdown()
        if cls.srvr.isAlive():
            print("prob")

    def testExecute(self):
        q = sla.SLAQuery("http://localhost:{0}/sla".format(testserverport))
        q.wavelength = "0.00260075/0.00260080"
        results = q.execute()
        self.assert_(isinstance(results, sla.SLAResults))
        self.assertEquals(results.nrecs, 21)

    def testSearch(self):
        srv = sla.SLAService("http://localhost:{0}/sla".format(testserverport))
        results = srv.search(wavelength="0.00260075/0.00260080")
        self.assert_(isinstance(results, sla.SLAResults))
        self.assertEquals(results.nrecs, 21)

        qurl = results.queryurl
        self.assert_("REQUEST=queryData" in qurl)
        self.assert_("WAVELENGTH=0.00260075%2F0.00260080" in qurl)


    def testSla(self):
        results = sla.search("http://localhost:{0}/sla".format(testserverport),
                             wavelength="0.00260075/0.00260080")
        self.assert_(isinstance(results, sla.SLAResults))
        self.assertEquals(results.nrecs, 21)

    def testError(self):
        srv = sla.SLAService("http://localhost:{0}/err".format(testserverport))
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
