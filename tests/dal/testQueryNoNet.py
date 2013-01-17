#!/usr/bin/env python
"""
Tests for vaopy.dal.query
"""
import os, sys, shutil, re, imp
import unittest, pdb
from urllib2 import URLError, HTTPError

import vaopy.dal.query as dalq
import vaopy.dal.dbapi2 as daldbapi
# from astropy.io.vo import parse as votableparse
from astropy.io.vo.tree import VOTableFile
from vaopy.dal.query import _votableparse as votableparse

testdir = os.path.dirname(sys.argv[0])
if not testdir:  testdir = "tests"
siaresultfile = "neat-sia.xml"
testserverport = 8081

try:
    t = "aTestSIAServer"
    mod = imp.find_module(t, [testdir])
    testserver = imp.load_module(t, mod[0], mod[1], mod[2])
    testserver.testdir = testdir
except ImportError, e:
    print >> sys.stderr, "Can't find test server: aTestSIAServer.py:", str(e)

class DalAccessErrorTest(unittest.TestCase):

    msg = "nya-nya"
    url = "http://localhost"

    def testProperties2(self):
        e = dalq.DalAccessError(self.msg, self.url)
        self.assertEquals(self.msg, e.reason)
        self.assertEquals(self.url, e.url)

        e.reason = "poof"
        self.assertEquals("poof", e.reason)
        del e.reason
        self.assertEquals(dalq.DalAccessError._defreason, e.reason)

    def testProperties1(self):
        e = dalq.DalAccessError(self.msg)
        self.assertEquals(self.msg, e.reason)
        self.assert_(e.url is None)

    def testPropertiesDef(self):
        e = dalq.DalAccessError()
        self.assertEquals(dalq.DalAccessError._defreason, e.reason)
        self.assert_(e.url is None)


class DalServiceErrorTest(unittest.TestCase):

    msg = "nya-nya"
    code = 404
    url = "http://localhost/"

    def testProperties4(self):
        c = HTTPError("http://localhost/", self.code, self.msg, None, None)
        e = dalq.DalServiceError(self.msg, self.code, c, self.url)
        self.assertEquals(self.msg, e.reason)
        self.assert_(e.cause is c)
        self.assertEquals(self.code, e.code)
        self.assertEquals(self.url, e.url)

        del e.cause 
        self.assert_(e.cause is None)
        e.cause = c
        self.assert_(e.cause is c)

        e.code = 505
        self.assertEquals(505, e.code)
        del e.code
        self.assert_(e.code is None)

    def testProperties3(self):
        c = HTTPError("http://localhost/", self.code, self.msg, None, None)
        e = dalq.DalServiceError(self.msg, self.code, c)
        self.assertEquals(self.msg, e.reason)
        self.assert_(e.cause is c)
        self.assertEquals(self.code, e.code)
        self.assert_(e.url is None)

    def testProperties2(self):
        e = dalq.DalServiceError(self.msg, self.code)
        self.assertEquals(self.msg, e.reason)
        self.assert_(e.cause is None)
        self.assertEquals(self.code, e.code)
        self.assert_(e.url is None)
        
    def testProperties1(self):
        e = dalq.DalServiceError(self.msg)
        self.assertEquals(self.msg, e.reason)
        self.assert_(e.cause is None)
        self.assert_(e.code is None)
        self.assert_(e.url is None)
        
    def testPropertiesDef(self):
        e = dalq.DalServiceError()
        self.assert_(e.reason and e.reason.startswith("Unknown service "))
        self.assert_(e.cause is None)
        self.assert_(e.code is None)
        self.assert_(e.url is None)

    def testFromExceptHTTP(self):
        url = "http://localhost/"
        c = HTTPError(url, self.code, self.msg, None, None)
        e = dalq.DalServiceError.from_except(c)
        self.assertEquals(self.msg, e.reason)
        self.assert_(e.cause is c)
        self.assertEquals(self.code, e.code)
        self.assertEquals(url, e.url)

    def testFromExceptURL(self):
        url = "http://localhost/"
        c = URLError(self.msg)
        e = dalq.DalServiceError.from_except(c, url)
        self.assertEquals(self.msg, e.reason)
        self.assert_(e.cause is c)
        self.assert_(e.code is None)
        self.assertEquals(url, e.url)

    def testFromExcept(self):
        c = RuntimeError(self.msg)
        e = dalq.DalServiceError.from_except(c)
        self.assertEquals(e.reason, "RuntimeError: " + self.msg)
        self.assert_(e.cause is c)
        self.assert_(e.code is None)
        self.assert_(e.url is None)

class DalQueryErrorTest(unittest.TestCase):

    msg = "nya-nya"
    label = "goofed"

    def testProperties2(self):
        e = dalq.DalQueryError(self.msg, self.label)
        self.assertEquals(self.msg, e.reason)
        self.assertEquals(self.label, e.label)

        e.reason = "poof"
        self.assertEquals("poof", e.reason)

        e.label = "OVERFLOW"
        self.assertEquals("OVERFLOW", e.label)
        del e.label
        self.assert_(e.label is None)

    def testProperties1(self):
        e = dalq.DalQueryError(self.msg)
        self.assertEquals(self.msg, e.reason)
        self.assert_(e.label is None)

    def testPropertiesDef(self):
        e = dalq.DalQueryError()
        self.assert_(e.reason and e.reason.startswith("Unknown DAL Query "))
        self.assert_(e.label is None)


class DalResultsTest(unittest.TestCase):

    def setUp(self):
        resultfile = os.path.join(testdir, siaresultfile)
        self.tbl = votableparse(resultfile)

    def testCtor(self):
        self.result = dalq.DalResults(self.tbl)
        self.assert_(isinstance(self.result._fldnames, list))
        self.assert_(self.result._tbl is not None)

    def testProps(self):
        self.testCtor()
        self.assertEquals(self.result.rowcount, 2)
        try:
            self.result.rowcount = 4
            self.fail("size is not read-only")
        except AttributeError:
            pass

        names = self.result.fieldnames()
        self.assert_(isinstance(names, list))
        self.assertEquals(len(names), 10)
        for i in xrange(len(names)):
            self.assert_(isinstance(names[i], str) or 
                         isinstance(names[i], unicode),
                         "field name #%d not a string: %s" % (i,type(names[i]))) 
            self.assert_(len(names[i]) > 0, "field name #%s is empty" % i)

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
        self.assertEquals(self.result.getvalue("Format", 0), "image/fits")
        self.assertEquals(self.result.getvalue("Format", 1), "image/jpeg")
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
        resultfile = os.path.join(testdir, siaresultfile)
        self.tbl = votableparse(resultfile)
        self.result = dalq.DalResults(self.tbl)
        self.rec = self.result.getrecord(0)

    def testFields(self):
        fnames = self.result.fieldnames()
        reckeys = self.rec.keys()
        for name in fnames:
            self.assert_(name in reckeys, "Missing fieldname: "+name)

    def testValues(self):
        self.assertEquals(self.rec["Format"], "image/fits")
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

class EnsureBaseURLTest(unittest.TestCase):

    def testFix(self):
        self.assertEquals(dalq.ensure_baseurl("http://localhost")[-1], '?')
        self.assertEquals(dalq.ensure_baseurl("http://localhost/sia")[-1], '?')
        self.assertEquals(dalq.ensure_baseurl("http://localhost/sia?cat=neat")[-1], '&')
        self.assertEquals(dalq.ensure_baseurl("http://localhost/sia?cat=neat&usecache=yes")[-1], '&')

        self.assertEquals(dalq.ensure_baseurl("http://localhost?"), 
                          "http://localhost?")
        self.assertEquals(dalq.ensure_baseurl("http://localhost/sia?"), 
                          "http://localhost/sia?")
        self.assertEquals(dalq.ensure_baseurl("http://localhost/sia?cat=neat&"), 
                          "http://localhost/sia?cat=neat&")
        self.assertEquals(dalq.ensure_baseurl("http://localhost/sia?cat=neat&usecache=yes&"), 
                          "http://localhost/sia?cat=neat&usecache=yes&")

class DalServiceTest(unittest.TestCase):

    def setUp(self):
        self.baseurl = "http://localhost/sia"

    def testCtor(self):
        self.res = {"title": "Archive", "shortName": "arch"}
        self.srv = dalq.DalService(self.baseurl, "sga", "2.0", self.res)

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

        self.assertEquals(self.srv.description["title"], "Archive")
        self.assertEquals(self.srv.description["shortName"], "arch")
        self.srv.description["title"] = "Sir"
        self.assertEquals(self.res["title"], "Archive")

    def testNoResmeta(self):
        srv = dalq.DalService(self.baseurl)
        self.assertEquals(srv.baseurl, self.baseurl)
        self.assert_(srv.description is not None)
        self.assert_(hasattr(srv.description, "get"))
        self.assertEquals(len(srv.description.keys()), 0)

    def testCreateQuery(self):
        self.testCtor()
        q = self.srv.create_query()
        self.assert_(isinstance(q, dalq.DalQuery))
        self.assertEquals(q.baseurl, self.baseurl)
        self.assertEquals(q.protocol, self.protocol)
        self.assertEquals(q.version, self.version)

class DalQueryTest(unittest.TestCase):

    def setUp(self):
        self.baseurl = "http://localhost/sia"

    def testCtor(self):
        self.query = dalq.DalQuery(self.baseurl, "sga", "2.0")
        self.assert_(self.query.getparam("format") is None)

    def testProps(self):
        self.testCtor()
        self.assertEquals(self.query.baseurl, self.baseurl)
        self.assertEquals(self.query.query, "sga")
        self.assertEquals(self.query.baseurl, "2.0")

    def testParam(self):
        self.testCtor()
        self.assertEquals(len(self.query.paramnames()), 0,
                          "param set should be empty: " + 
                          str(self.query.paramnames()))
        self.assert_(self.query.getparam("RA") is None)

        self.query.setparam("RA", 51.235)
        self.assertEquals(len(self.query.paramnames()), 1)
        self.assertEquals(self.query.getparam("RA"), 51.235)

        self.query.setparam("RA", 127.235)
        self.assertEquals(len(self.query.paramnames()), 1)
        self.assertEquals(self.query.getparam("RA"), 127.235)

        self.query.setparam("DEC", -13.49677)
        self.assertEquals(len(self.query.paramnames()), 2)
        self.assertEquals(self.query.getparam("DEC"), -13.49677)

        self.query.unsetparam("FORMAT")
        self.assertEquals(len(self.query.paramnames()), 2)

        self.query.unsetparam("RA")
        self.assertEquals(len(self.query.paramnames()), 1)
        self.assertEquals(self.query.getparam("DEC"), -13.49677)
        self.assert_(self.query.getparam("RA") is None)

    def testQueryURL(self):
        self.testCtor()
        self.query.setparam("RA", 51.235)
        qurl = self.query.getqueryurl()
        self.assertEquals(qurl, self.baseurl+'?RA=51.235')

        self.query.setparam("DEC", -13.49677)
        qurl = self.query.getqueryurl()
        self.assert_(qurl == self.baseurl+'?RA=51.235&DEC=-13.49677' or
                     qurl == self.baseurl+'?DEC=-13.49677&RA=51.235')

        self.query.setparam("SR", "1.0")
        qurl = self.query.getqueryurl()
        self.assert_(qurl == self.baseurl+'?RA=51.235&SR=1.0&DEC=-13.49677' or
                     qurl == self.baseurl+'?DEC=-13.49677&SR=1.0&RA=51.235' or 
                     qurl == self.baseurl+'?RA=51.235&DEC=-13.49677&SR=1.0' or
                     qurl == self.baseurl+'?DEC=-13.49677&RA=51.235&SR=1.0' or 
                     qurl == self.baseurl+'?SR=1.0&DEC=-13.49677&RA=51.235' or 
                     qurl == self.baseurl+'?SR=1.0&RA=51.235&DEC=-13.49677')

    def testEncode(self):
        self.testCtor()
        self.query.setparam("NaMe", "a val")
        qurl = self.query.getqueryurl()
        self.assertEquals(qurl, self.baseurl+'?NaMe=a+val')
        
        self.testCtor()
        self.query.setparam("NaMe", "a+val")
        qurl = self.query.getqueryurl()
        self.assertEquals(qurl, self.baseurl+'?NaMe=a%2Bval')

    def testEncodeList(self):
        self.testCtor()
        self.query.setparam("POS", (5.231, -13.441))
        qurl = self.query.getqueryurl()
        self.assertEquals(qurl, self.baseurl+'?POS=5.231,-13.441')
        

class QueryExecuteTest(unittest.TestCase):

    def setUp(self):
        pass
        # self.srvr = testserver.TestServer(testserverport)
        # self.srvr.start()

    def tearDown(self):
        pass 
        #if self.srvr.isAlive():
        #    self.srvr.shutdown()
        #if self.srvr.isAlive():
        #    print "prob"

    def testExecute(self):
        q = dalq.DalQuery("http://localhost:%d/sia" % testserverport)
        q.setparam("foo", "bar")
        # pdb.set_trace()
        results = q.execute()
        self.assert_(isinstance(results, dalq.DalResults))
        self.assertEquals(results.rowcount, 2)

    def testExecuteStream(self):
        q = dalq.DalQuery("http://localhost:%d/sia" % testserverport)
        q.setparam("foo", "bar")
        # pdb.set_trace()
        strm = q.execute_stream()
        self.assert_(strm is not None)
        self.assert_(hasattr(strm, "read"))
        results = strm.read()
        strm.close()
        self.assert_(results.startswith("<?xml version="))

    def testExecuteRaw(self):
        q = dalq.DalQuery("http://localhost:%d/sia" % testserverport)
        q.setparam("foo", "bar")
        # pdb.set_trace()
        data = q.execute_raw()
        self.assert_(data is not None)
        self.assert_(isinstance(data, unicode) or isinstance(data, str))
        self.assert_(data.startswith("<?xml version="))

    def testExecuteVotable(self):
        q = dalq.DalQuery("http://localhost:%d/sia" % testserverport)
        q.setparam("foo", "bar")
        # pdb.set_trace()
        results = q.execute_votable()
        self.assert_(isinstance(results, VOTableFile))

    def testExecuteServiceErr(self):
        q = dalq.DalQuery("http://localhost:%d/goob" % testserverport)
        q.setparam("foo", "bar")
        # pdb.set_trace()
        self.assertRaises(dalq.DalServiceError, q.execute)

    def testExecuteRawServiceErr(self):
        q = dalq.DalQuery("http://localhost:%d/goob" % testserverport)
        q.setparam("foo", "bar")
        # pdb.set_trace()
        self.assertRaises(dalq.DalServiceError, q.execute_raw)

    def testExecuteStreamServiceErr(self):
        q = dalq.DalQuery("http://localhost:%d/goob" % testserverport)
        q.setparam("foo", "bar")
        # pdb.set_trace()
        try:
            q.execute_raw()
            self.fail("failed to raise exception on bad url")
        except dalq.DalServiceError, e:
            self.assertEquals(e.code, 404)
            self.assertEquals(e.reason, "Not Found")
            self.assert_(isinstance(e.cause, HTTPError))
        except Exception, e:
            self.fail("wrong exception raised: " + str(type(e)))


    def testExecuteVotableServiceErr(self):
        q = dalq.DalQuery("http://localhost:%d/goob" % testserverport)
        q.setparam("foo", "bar")
        # pdb.set_trace()
        self.assertRaises(dalq.DalServiceError, q.execute_votable)

    def testExecuteRawQueryErr(self):
        q = dalq.DalQuery("http://localhost:%d/err" % testserverport)
        q.setparam("foo", "bar")
        # pdb.set_trace()
        data = q.execute_raw()
        self.assert_(data is not None)
        self.assert_(isinstance(data, unicode) or isinstance(data, str))
        self.assert_(data.startswith("<?xml version="))
        self.assert_('<INFO name="QUERY_STATUS" value="ERR' in data)

    def testExecuteQueryErr(self):
        q = dalq.DalQuery("http://localhost:%d/err" % testserverport)
        q.setparam("foo", "bar")
        # pdb.set_trace()
        try:
            q.execute()
            self.fail("failed to raise exception for syntax error")
        except dalq.DalQueryError, e:
            self.assertEquals(e.label, "ERROR")
            self.assertEquals(str(e), "Forced Fail")
        except dalq.DalServiceError, e:
            self.fail("wrong exception raised: DalServiceError: " + str(e))
        except Exception, e:
            self.fail("wrong exception raised: " + str(type(e)))


__all__ = "DalAccessErrorTest DalServiceErrorTest DalQueryErrorTest RecordTest EnsureBaseURLTest DalServiceTest DalQueryTest QueryExecuteTest".split()
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
