#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.dal.query
"""
from __future__ import print_function, division

import os, sys, shutil, re, imp, glob, tempfile, random, time
import unittest, pdb

import pyvo.dal.query as dalq
import pyvo.dal.dbapi2 as daldbapi
# from astropy.io.vo import parse as votableparse
from astropy.io.votable.tree import VOTableFile
from pyvo.dal.query import _votableparse as votableparse
from astropy.utils.data import get_pkg_data_filename
from . import aTestDALServer as testserve
import requests

siaresultfile = "data/neat-sia.xml"
ssaresultfile = "data/jhu-ssa.xml"
testserverport = 8084
testserverport += 10
testserverport += random.randint(0,9)

testserver = None

# def setup_module(module):
#     """
#     module level setup: start test server
#     """
#     testserver = testserve.TestServer(testserverport)
#     testserver.start()

# def teardown_module(module):
#     """
#     terminate the test server
#     """
#     if testserver and testserver.is_alive():
#         testserver.terminate()

class DALAccessErrorTest(unittest.TestCase):

    msg = "nya-nya"
    url = "http://localhost"

    def testProperties2(self):
        e = dalq.DALAccessError(self.msg, self.url)
        self.assertEquals(self.msg, e.reason)
        self.assertEquals(self.url, e.url)

        e.reason = "poof"
        self.assertEquals("poof", e.reason)
        del e.reason
        self.assertEquals(dalq.DALAccessError._defreason, e.reason)

    def testProperties1(self):
        e = dalq.DALAccessError(self.msg)
        self.assertEquals(self.msg, e.reason)
        self.assert_(e.url is None)

    def testPropertiesDef(self):
        e = dalq.DALAccessError()
        self.assertEquals(dalq.DALAccessError._defreason, e.reason)
        self.assert_(e.url is None)


class DALServiceErrorTest(unittest.TestCase):

    msg = "nya-nya"
    code = 404
    url = "http://localhost/"

    def testProperties2(self):
        e = dalq.DALServiceError(self.msg, self.code)
        self.assertEquals(self.msg, e.reason)
        self.assert_(e.cause is None)
        self.assertEquals(self.code, e.code)
        self.assert_(e.url is None)
        
    def testProperties1(self):
        e = dalq.DALServiceError(self.msg)
        self.assertEquals(self.msg, e.reason)
        self.assert_(e.cause is None)
        self.assert_(e.code is None)
        self.assert_(e.url is None)
        
    def testPropertiesDef(self):
        e = dalq.DALServiceError()
        self.assert_(e.reason and e.reason.startswith("Unknown service "))
        self.assert_(e.cause is None)
        self.assert_(e.code is None)
        self.assert_(e.url is None)

    def testFromExcept(self):
        c = RuntimeError(self.msg)
        e = dalq.DALServiceError.from_except(c)
        self.assertEquals(e.reason, "RuntimeError: " + self.msg)
        self.assert_(e.cause is c)
        self.assert_(e.code is None)
        self.assert_(e.url is None)

class DALQueryErrorTest(unittest.TestCase):

    msg = "nya-nya"
    label = "goofed"

    def testProperties2(self):
        e = dalq.DALQueryError(self.msg, self.label)
        self.assertEquals(self.msg, e.reason)
        self.assertEquals(self.label, e.label)

        e.reason = "poof"
        self.assertEquals("poof", e.reason)

        e.label = "OVERFLOW"
        self.assertEquals("OVERFLOW", e.label)
        del e.label
        self.assert_(e.label is None)

    def testProperties1(self):
        e = dalq.DALQueryError(self.msg)
        self.assertEquals(self.msg, e.reason)
        self.assert_(e.label is None)

    def testPropertiesDef(self):
        e = dalq.DALQueryError()
        self.assert_(e.reason and e.reason.startswith("Unknown DAL Query "))
        self.assert_(e.label is None)


class DALResultsTest(unittest.TestCase):

    def setUp(self):
        resultfile = get_pkg_data_filename(siaresultfile)
        self.tbl = votableparse(resultfile)

    def testCtor(self):
        self.result = dalq.DALResults(self.tbl)
        self.assert_(isinstance(self.result._fldnames, list))
        self.assert_(self.result.votable is not None)

    def testProps(self):
        self.testCtor()
        self.assertEquals(self.result.nrecs, 2)
        try:
            self.result.nrecs = 4
            self.fail("size is not read-only")
        except AttributeError:
            pass

        names = self.result.fieldnames()
        self.assert_(isinstance(names, list))
        self.assertEquals(len(names), 10)
        for i in xrange(len(names)):
            self.assert_(isinstance(names[i], str) or 
                         isinstance(names[i], unicode),
                 "field name #{0} not a string: {1}".format(i,type(names[i]))) 
            self.assert_(len(names[i]) > 0, "field name #{0} is empty".format(i))

        fd = self.result.fielddesc()
        self.assert_(isinstance(fd, list))
        self.assertEquals(len(fd), 10)
        for fld in fd:
            self.assert_(hasattr(fld,'name'))
            self.assert_(hasattr(fld,'ID'))
            self.assert_(hasattr(fld,'ucd'))
            self.assert_(hasattr(fld,'datatype'))

        for i in xrange(len(names)):
            fld = self.result.getdesc(names[i])
            self.assert_(fld is fd[i])

        fld = self.result.getdesc("Format")
        self.assertEquals(fld.name, "Format")
        # self.assertEquals(fld.ID, "Format")
        self.assertEquals(fld.ucd, "VOX:Image_Format")
        self.assertEquals(fld.datatype, "char")
        self.assertEquals(fld.arraysize, "*")
        self.assert_(fld.utype is None)

    def testValue(self):
        self.testCtor()
        self.assertEquals(self.result.getvalue("Format", 0), b"image/fits")
        self.assertEquals(self.result.getvalue("Format", 1), b"image/jpeg")
        self.assertEquals(self.result.getvalue("Dim", 0), 2)
        val = self.result.getvalue("Size", 0)
        self.assertEquals(len(val), 2)
        self.assertEquals(val[0], 300)
        self.assertEquals(val[1], 300)
        self.assertRaises(ValueError, self.result.getvalue, "Goober", 0)

    def testGetRecord(self):
        self.testCtor()
        rec = self.result.getrecord(0)
        self.assert_(rec is not None)
        self.assert_(isinstance(rec, dalq.Record))
        rec = self.result.getrecord(1)
        self.assert_(rec is not None)
        self.assert_(isinstance(rec, dalq.Record))
        self.assertRaises(IndexError, self.result.getrecord, 2)

    def testGetColumn(self):
        self.testCtor()
        col = self.result.getcolumn('Ra')
        shifted = col + 0.05
        self.assertAlmostEquals(0.05, shifted[0]-col[0])
        self.assertRaises(ValueError, self.result.getcolumn, 'goob')

    def testIter(self):
        self.testCtor()
        i = 0
        for rec in self.result:
            self.assert_(rec is not None)
            self.assert_(isinstance(rec, dalq.Record))
            i += 1
        self.assertEquals(i, 2)

    def testCursor(self):
        self.testCtor()
        c = self.result.cursor()
        self.assert_(c is not None)
        self.assert_(isinstance(c, daldbapi.Cursor))

    def testByUcd(self):
        self.testCtor()
        self.assertEquals(self.result.fieldname_with_ucd("POS_EQ_RA_MAIN"),"Ra")
        self.assertEquals(self.result.fieldname_with_ucd("VOX:Image_AccessReference"),"URL")


class RecordTest(unittest.TestCase):

    def setUp(self):
        resultfile = get_pkg_data_filename(siaresultfile)
        self.tbl = votableparse(resultfile)
        self.result = dalq.DALResults(self.tbl)
        self.rec = self.result.getrecord(0)

    def testFields(self):
        fnames = self.result.fieldnames()
        reckeys = self.rec.keys()
        for name in fnames:
            self.assert_(name in reckeys, "Missing fieldname: "+name)

    def testValues(self):
        self.assertEquals(self.rec["Format"], b"image/fits")
        self.assertEquals(self.rec["Dim"], 2)
        val = self.rec["Size"]
        self.assertEquals(len(val), 2)
        self.assertEquals(val[0], 300)
        self.assertEquals(val[1], 300)
        try:
            self.rec["Goober"]
            self.fail("Failed to raise KeyError on bad key")
        except KeyError:
            pass

    def testSuggestExtension(self):
        self.assertEquals(self.rec.suggest_extension("goob"), "goob")
        self.assert_(self.rec.suggest_extension() is None)

    def testHasKey(self):
        self.assertEquals(self.rec["Format"], b"image/fits")
        self.assertTrue(self.rec.has_key('Format'))
        self.assertTrue('Format' in self.rec)
        self.assertFalse(self.rec.has_key('Goober'))
        self.assertFalse('Goober' in self.rec)

class MimeCheckTestCase(unittest.TestCase):
    
    def testGood(self):
        self.assertTrue(dalq.is_mime_type("image/jpeg"))
        self.assertTrue(dalq.is_mime_type("application/fits"))
        self.assertTrue(dalq.is_mime_type("application/x-fits"))
        self.assertTrue(dalq.is_mime_type("application/fits"))
        self.assertTrue(dalq.is_mime_type("application/votable+xml"))
        self.assertTrue(dalq.is_mime_type("application/fits;convention=STScI-STIS"))

    def testBad(self):
        self.assertFalse(dalq.is_mime_type("image"))
        self.assertFalse(dalq.is_mime_type("image/votable/xml"))

class DALServiceTest(unittest.TestCase):

    def setUp(self):
        self.baseurl = "http://localhost/sia"

    def testCtor(self):
        self.res = {"title": "Archive", "shortName": "arch"}
        self.srv = dalq.DALService(self.baseurl, "sga", "2.0", self.res)

    def testCtorSimpleResource(self):
        import pyvo.registry.vao as reg
        regresultfile = \
            get_pkg_data_filename("../../registry/tests/data/reg-short.xml")
        res = dalq.DALResults(votableparse(regresultfile))
        # import pytest; pytest.set_trace()
        srv = dalq.DALService(self.baseurl, "sga", "3.0", 
                              reg.SimpleResource(res, 0))
        self.assertTrue(len(srv.info.keys()) > 0)
        self.assertTrue(srv.info.get("title") is not None)

    def testProps(self):
        self.testCtor()
        self.assertEquals(self.srv.baseurl, self.baseurl)
        self.assertEquals(self.srv.protocol, "sga")
        self.assertEquals(self.srv.version, "2.0")
        try:
            self.srv.baseurl = "goober"
            self.fail("baseurl not read-only")
        except AttributeError:
            pass
        try:
            self.srv.protocol = "sia"
            self.fail("protocol not read-only")
        except AttributeError:
            pass
        try:
            self.srv.version = "1.0"
            self.fail("version not read-only")
        except AttributeError:
            pass

        self.assertEquals(self.srv.info["title"], "Archive")
        self.assertEquals(self.srv.info["shortName"], "arch")
        self.srv.info["title"] = "Sir"
        self.assertEquals(self.res["title"], "Archive")

    def testNoResmeta(self):
        srv = dalq.DALService(self.baseurl)
        self.assertEquals(srv.baseurl, self.baseurl)
        self.assert_(srv.info is not None)
        self.assert_(hasattr(srv.info, "get"))
        self.assertEquals(len(srv.info.keys()), 0)

    def testCreateQuery(self):
        self.testCtor()
        q = self.srv.create_query()
        self.assert_(isinstance(q, dalq.DALQuery))
        self.assertEquals(q.baseurl, self.baseurl)
        self.assertEquals(q.protocol, self.srv.protocol)
        self.assertEquals(q.version, self.srv.version)

    def testCreateQueryWithKws(self):
        self.testCtor()
        q = self.srv.create_query(RA=12.045, DEC=-13.08, SR=0.01)
        self.assert_(isinstance(q, dalq.DALQuery))
        self.assertEquals(q.baseurl, self.baseurl)
        self.assertEquals(q.protocol, self.srv.protocol)
        self.assertEquals(q.version, self.srv.version)
        self.assertAlmostEquals(q.get('RA'), 12.045)
        self.assertAlmostEquals(q.get('DEC'), -13.08)
        self.assertAlmostEquals(q.get('SR'), 0.01)



class DALQueryTest(unittest.TestCase):

    def setUp(self):
        self.baseurl = "http://localhost/sia"

    def testCtor(self):
        self.query = dalq.DALQuery(self.baseurl, "sga", "2.0")
        self.assert_(self.query.get("format") is None)

    def testProps(self):
        self.testCtor()
        self.assertEquals(self.query.baseurl, self.baseurl)
        self.assertEquals(self.query.protocol, "sga")
        self.assertEquals(self.query.version, "2.0")

        self.query.baseurl = "http://gomer.net/infinite/loop?"
        self.assertEquals(self.query.baseurl, 
                          "http://gomer.net/infinite/loop?");

    def testParam(self):
        self.testCtor()
        self.assertEquals(len(self.query.keys()), 0,
                          "param set should be empty: " + 
                          str(self.query.keys()))
        self.assert_(self.query.get("RA") is None)

        self.query["RA"] = 51.235
        self.assertEquals(len(self.query.keys()), 1)
        self.assertEquals(self.query.get("RA"), 51.235)

        self.query["RA"] = 127.235
        self.assertEquals(len(self.query.keys()), 1)
        self.assertEquals(self.query.get("RA"), 127.235)

        self.query["DEC"] = -13.49677
        self.assertEquals(len(self.query.keys()), 2)
        self.assertEquals(self.query.get("DEC"), -13.49677)

        del self.query["RA"]
        self.assertEquals(len(self.query.keys()), 1)
        self.assertEquals(self.query.get("DEC"), -13.49677)
        self.assert_(self.query.get("RA") is None)
        

class QueryExecuteTest(unittest.TestCase):

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
        q = dalq.DALQuery("http://localhost:{0}/sia".format(self.srvr.port))
        q["foo"] = "bar"
        # pdb.set_trace()
        results = q.execute()
        self.assert_(isinstance(results, dalq.DALResults))
        self.assertEquals(results.nrecs, 2)

    def testExecuteStream(self):
        q = dalq.DALQuery("http://localhost:{0}/sia".format(self.srvr.port))
        q["foo"] = "bar"
        # pdb.set_trace()
        strm = q.execute_stream()
        self.assert_(strm is not None)
        self.assert_(hasattr(strm, "read"))
        results = strm.read()
        strm.close()
        self.assert_(results.startswith(b"<?xml version="))

    def testExecuteRaw(self):
        q = dalq.DALQuery("http://localhost:{0}/sia".format(self.srvr.port))
        q["foo"] = "bar"
        # pdb.set_trace()
        data = q.execute_raw()
        self.assert_(data is not None)
        if sys.version_info[0] >= 3:
            self.assert_(isinstance(data, str) or isinstance(data, bytes))
        else:
            self.assert_(isinstance(data, unicode) or isinstance(data, str))
        self.assert_(data.startswith(b"<?xml version="))

    def testExecuteVotable(self):
        q = dalq.DALQuery("http://localhost:{0}/sia".format(self.srvr.port))
        q["foo"] = "bar"
        # pdb.set_trace()
        results = q.execute_votable()
        self.assert_(isinstance(results, VOTableFile))

    def testExecuteServiceErr(self):
        q = dalq.DALQuery("http://localhost:{0}/goob".format(self.srvr.port))
        q["foo"] = "bar"
        # pdb.set_trace()
        self.assertRaises(dalq.DALServiceError, q.execute)

    def testExecuteRawServiceErr(self):
        q = dalq.DALQuery("http://localhost:{0}/goob".format(self.srvr.port))
        q["foo"] = "bar"
        # pdb.set_trace()
        self.assertRaises(dalq.DALServiceError, q.execute_raw)

    def testExecuteStreamServiceErr(self):
        q = dalq.DALQuery("http://localhost:{0}/goob".format(self.srvr.port))
        q["foo"] = "bar"
        # pdb.set_trace()
        try:
            q.execute_stream()
            self.fail("failed to raise exception on bad url")
        except dalq.DALServiceError as e:
            self.assertEquals(e.code, 404)
            self.assertIn("not found", e.reason.lower())
            self.assert_(isinstance(e.cause, requests.RequestException))
        except Exception as e:
            self.fail("wrong exception raised: " + str(type(e)))


    def testExecuteVotableServiceErr(self):
        q = dalq.DALQuery("http://localhost:{0}/goob".format(self.srvr.port))
        q["foo"] = "bar"
        # pdb.set_trace()
        self.assertRaises(dalq.DALServiceError, q.execute_votable)

    def testExecuteRawQueryErr(self):
        q = dalq.DALQuery("http://localhost:{0}/err".format(self.srvr.port))
        q["foo"] = "bar"
        # pdb.set_trace()
        data = q.execute_raw()
        self.assert_(data is not None)
        if sys.version_info[0] >= 3:
            self.assert_(isinstance(data, str) or isinstance(data, bytes))
        else:
            self.assert_(isinstance(data, unicode) or isinstance(data, str))
        self.assert_(data.startswith(b"<?xml version="))
        self.assert_(b'<INFO name="QUERY_STATUS" value="ERR' in data)

    def testExecuteQueryErr(self):
        q = dalq.DALQuery("http://localhost:{0}/err".format(self.srvr.port))
        q["foo"] = "bar"
        # pdb.set_trace()
        try:
            q.execute()
            self.fail("failed to raise exception for syntax error")
        except dalq.DALQueryError as e:
            self.assertEquals(e.label, "ERROR")
            self.assertEquals(str(e), "Forced Fail")
        except dalq.DALServiceError as e:
            self.fail("wrong exception raised: DALServiceError: " + str(e))
        except Exception as e:
            self.fail("wrong exception raised: " + str(type(e)))


class CursorTest(unittest.TestCase):

    def setUp(self):
        resultfile = get_pkg_data_filename(ssaresultfile)
        self.tbl = votableparse(resultfile)

    def testCtor(self):
        self.result = dalq.DALResults(self.tbl)
        self.assert_(isinstance(self.result._fldnames, list))
        self.assert_(self.result.votable is not None)
        self.cursor = self.result.cursor()

    def testCursor(self):
        self.testCtor()
        self.assert_(self.cursor is not None)
        self.assert_(isinstance(self.cursor, daldbapi.Cursor))
        self.assertEquals(self.cursor.rowcount, 35)
        self.assertEquals(self.cursor.arraysize, 1)    
        descr = self.cursor.description
        self.assert_(len(descr) > 0)
        self.assertEquals(descr[1][0], 'AcRef')
        self.assert_(isinstance(descr[1][1], daldbapi.TypeObject))

    def testInfos(self):
        self.testCtor()
        infos = self.cursor.infos()
        self.assertEquals(int(infos['TableRows']), 35)

    def testFetchOne(self):
        self.testCtor()
        pos = self.cursor.pos
        rec = self.cursor.fetchone()
        self.assertEquals(self.cursor.pos, pos + 1)
        rec2 = self.cursor.fetchone()
#        self.assert_(rec != rec2)
        self.assertEquals(self.cursor.pos, pos + 2)

    def testFetchMany(self):
        self.testCtor()
        pos = self.cursor.pos
        recs = self.cursor.fetchmany()
        self.assertEquals(len(recs), self.cursor.arraysize)         
        recs = self.cursor.fetchmany(size = 5)
        self.assertEquals(len(recs), 5)
        recs = self.cursor.fetchmany(size = -5)

    def testFetchAll(self):
        self.testCtor()
        recs = self.cursor.fetchall()
        self.assertEquals(len(recs), 35)

        self.testCtor()
        self.cursor.fetchone()
        recs = self.cursor.fetchall()
        self.assertEquals(len(recs), 34)
        
    def testScroll(self):
        self.testCtor()
        pos = self.cursor.pos
        self.cursor.scroll(5)
        self.assertEquals(self.cursor.pos, pos + 5)
        self.cursor.scroll(5, mode = "absolute")
        self.assertEquals(self.cursor.pos, 5)
        try:
          self.cursor.scroll(-1, mode = "absolute")
        except daldbapi.DataError:
          pass
        self.cursor.scroll(-1)
        self.assertEquals(self.cursor.pos, 4)

class DatasetNameTest(unittest.TestCase):

    base = "testds"

    def setUp(self):
        resultfile = get_pkg_data_filename(siaresultfile)
        self.tbl = votableparse(resultfile)
        self.result = dalq.DALResults(self.tbl)
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

    def testMime2Ext(self):
        self.assertEquals("fits", dalq.mime2extension("application/fits"))
        self.assertEquals("fits", dalq.mime2extension("image/fits"))
        self.assertEquals("fits", dalq.mime2extension("image/x-fits"))
        self.assertEquals("jpg", dalq.mime2extension("image/jpeg"))
        self.assertEquals("gif", dalq.mime2extension("image/gif"))
        self.assertEquals("png", dalq.mime2extension("image/png"))
        self.assertEquals("txt", dalq.mime2extension("text/plain"))
        self.assertEquals("html", dalq.mime2extension("text/html"))
        self.assertEquals("xml", dalq.mime2extension("text/xml"))
        self.assertEquals("xml", dalq.mime2extension("application/votable;convention=stsci"))
        self.assertEquals("xml", dalq.mime2extension("application/x-votable"))
        self.assertEquals("xml", dalq.mime2extension("application/votable"))
        self.assertEquals("xls", 
               dalq.mime2extension("application/x-micrsoft-spreadsheet", "xls"))

    def testSuggest(self):
        self.assertEquals("dataset", self.rec.suggest_dataset_basename())
        self.assertEquals("DAT", self.rec.suggest_extension("DAT"))

    def testMakeDatasetName(self):
        self.assertTrue(os.path.isdir(self.outdir))
        self.assertEquals("./dataset.dat", self.rec.make_dataset_filename())
        self.assertEquals("./goober.dat", 
                          self.rec.make_dataset_filename(base="goober"))
        self.assertEquals("./dataset.fits", 
                          self.rec.make_dataset_filename(ext="fits"))
        self.assertEquals("./goober.fits", 
                          self.rec.make_dataset_filename(base="goober", 
                                                         ext="fits"))
                          
        self.assertEquals(self.outdir+"/dataset.dat", 
                          self.rec.make_dataset_filename(self.outdir))

        path = os.path.join(self.outdir,self.base+".dat")
        self.assertFalse(os.path.exists(path))
        self.assertEquals(path, 
                          self.rec.make_dataset_filename(self.outdir, self.base))
        open(path,'w').close()
        self.assertTrue(os.path.exists(path))
        path = os.path.join(self.outdir,self.base+"-1.dat")
        self.assertEquals(path, 
                          self.rec.make_dataset_filename(self.outdir, self.base))
        open(path,'w').close()
        self.assertTrue(os.path.exists(path))
        path = os.path.join(self.outdir,self.base+"-2.dat")
        self.assertEquals(path, 
                          self.rec.make_dataset_filename(self.outdir, self.base))
        open(path,'w').close()
        self.assertTrue(os.path.exists(path))
        path = os.path.join(self.outdir,self.base+"-3.dat")
        self.assertEquals(path, 
                          self.rec.make_dataset_filename(self.outdir, self.base))
                         
        self.cleanfiles()
        open(os.path.join(self.outdir,self.base+".dat"),'w').close()
        path = os.path.join(self.outdir,self.base+"-1.dat")
        self.assertEquals(path, 
                          self.rec.make_dataset_filename(self.outdir, self.base))
        open(os.path.join(self.outdir,self.base+"-1.dat"),'w').close()
        open(os.path.join(self.outdir,self.base+"-2.dat"),'w').close()
        open(os.path.join(self.outdir,self.base+"-3.dat"),'w').close()
        path = os.path.join(self.outdir,self.base+"-4.dat")
        self.assertEquals(path, 
                          self.rec.make_dataset_filename(self.outdir, self.base))

        self.cleanfiles()
        self.assertEquals(os.path.join(self.outdir,self.base+".dat"),
                          self.rec.make_dataset_filename(self.outdir, self.base))

class FormatTest(unittest.TestCase):

    subtests = [ ("d &lt; 10", "d < 10"),
                 ("t&lt;0",    "t<0"),
                 ("d &gt; 10", "d > 10"),
                 ("t&gt;0",    "t>0"),
                 ("A&amp;P",   "A&P"),
                 ("A &amp; P", "A & P"),
                 ("A &amp;amp;P", "A &amp;P"),
                 ("-30&#176; ", "-30 deg "),
                 ("-30\deg ", "-30 deg "),
                 ("I am. <br />", "I am. "),
                 ("I am; <br/> therefore", "I am;  therefore"),
                 ("I am;<br> therefore", "I am; therefore"),
                 ("<p>I am.</p><p>That's", "<p>I am.<p>That's"),
                 ("goes as $v ~ r$.", "goes as v ~ r."),
                 ("where $r$ is", "where r is"),
                 ("$-45\deg$", "-45 deg"),
                 ("upwards of $1M per month ($10M per", 
                  "upwards of $1M per month ($10M per")        ]

    splittests = [ "one\n\ntwo", "one<p>two", "one <p/> two", "one\para two" ]

    def test_simple_sub(self):
        for orig, trx in self.subtests:
            self.assertEquals(dalq.deref_markup(orig), trx)

    def test_mixed_sub(self):
        inp = """At t&gt;0, the drop goes as $1/r^2$. <br> This shows"""
        out = """At t>0, the drop goes as 1/r^2.  This shows"""
        self.assertEquals(dalq.deref_markup(inp), out);

    def test_fill(self):
        inp = """
The quick brown 
fox jumped over 
the lazy dogs.
"""
        out = """The quick brown fox jumped over the
lazy dogs."""

        self.assertEquals(dalq.para_format_desc(inp, 38), out)

    def test_para_detect(self):
        for t in self.splittests:
            self.assertEquals(dalq.para_format_desc(t), "one\n\ntwo")


    def test_para_format(self):
        inp = """This tests the paragraph formatting functionality that 
                 will be used to disply resource descriptions.  This is not 
                 meant for display purpoes only.

                 It must be able to handle to handle multiple paragrasphs.  
                 The normal delimiter is a pair of consecutive new-line 
                 charactere, but other markup will be recognized as well,
                 e.g. "&lt;p&gt;".  <p> Formatting must be succeesful for 
                 $n$ paragraphs where $n > 1$.  It should even work on $n^2$ 
                 paragraphs."""

        out = """This tests the paragraph formatting
functionality that will be used to
disply resource descriptions.  This is
not meant for display purpoes only.

It must be able to handle to handle
multiple paragrasphs. The normal
delimiter is a pair of consecutive new-
line charactere, but other markup will
be recognized as well, e.g. "<p>".

Formatting must be succeesful for n
paragraphs where n > 1.  It should even
work on n^2 paragraphs."""

        text = dalq.para_format_desc(inp, 40)
        if text != out:
            for i in range(len(text)):
                if text[i] != out[i]:
                    print("format different from expected starting with: "+
                          text[i:])
                    break
        self.assertEquals(text, out, "Incorrect formatting.")
                          
                 
__all__ = "DALAccessErrorTest DALServiceErrorTest DALQueryErrorTest RecordTest EnsureBaseURLTest DALServiceTest DALQueryTest QueryExecuteTest CursorTest DatasetNameTest FormatTest".split()
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

    srvr = testserve.get_server(testserverport)
    try:
        srvr.start()
        unittest.main()
    finally:
        if srvr.is_alive():
            srvr.terminate()

