#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.registry.vao
"""
from __future__ import print_function, division

import os, sys, shutil, re, imp
import unittest, pdb
from urllib2 import URLError, HTTPError

from ...dal import query as dalq
from .. import vao as reg
from astropy.io.votable.tree import VOTableFile
from ...dal.query import _votableparse as votableparse
from astropy.utils.data import get_pkg_data_filename

regresultfile = "data/reg-short.xml"


class RegServiceTest(unittest.TestCase):

    def testCtor(self):
        self.res = {"title": "VAO Registry", "shortName": "vaoreg"}
        self.srv = reg.RegistryService(resmeta=self.res)

    def testProps(self):
        self.testCtor()
        self.assertEquals(self.srv.baseurl, 
                          reg.RegistryService.STSCI_REGISTRY_BASEURL)
        try:
            self.srv.baseurl = "goober"
            self.fail("baseurl not read-only")
        except AttributeError:
            pass

        self.assertEquals(self.srv.description["title"], "VAO Registry")
        self.assertEquals(self.srv.description["shortName"], "vaoreg")
        self.srv.description["title"] = "Sir"
        self.assertEquals(self.res["title"], "VAO Registry")

    def testCreateQuery(self):
        self.testCtor()
        q = self.srv.create_query()
        self.assert_(isinstance(q, reg.RegistryQuery))
        self.assertEquals(q.baseurl, reg.RegistryService.STSCI_REGISTRY_BASEURL)
        self.assertEquals(len(q._param.keys()), 0)

    def testCreateQueryWithArgs(self):
        self.testCtor()
        q = self.srv.create_query(keywords=["galaxy", "AGN"], servicetype="sia",
                                  waveband="radio", 
                                  sqlpred="publisher like '%nrao%'")
        self.assert_(isinstance(q, reg.RegistryQuery))
        self.assertEquals(q.baseurl, reg.RegistryService.STSCI_REGISTRY_BASEURL)
        self.assertEquals(len(q._param.keys()), 0)

        self.assertEquals(q.waveband, "Radio")
        self.assertEquals(q.servicetype, "sia")
        self.assertEquals(len(q.keywords), 2)
        self.assertEquals(q.keywords[0], "galaxy")
        self.assertEquals(q.keywords[1], "AGN")

        self.assertEquals(len(q.predicates), 1)
        self.assertEquals(q.predicates[0], "publisher like '%nrao%'")

class RegQueryTest(unittest.TestCase):
    
    def testCtor(self):
        self.q = reg.RegistryQuery()

    def testWaveband(self):
        self.testCtor()
        self.assert_(self.q.waveband is None)
        self.q.waveband = "Radio"
        self.assert_(self.q.waveband is not None)
        self.assertEquals(self.q.waveband, "Radio")

        del self.q.waveband 
        self.assert_(self.q.waveband is None)

        self.q.waveband = "radio"
        self.assert_(self.q.waveband is not None)
        self.assertEquals(self.q.waveband, "Radio")

        self.q.waveband = "millimeter"
        self.assertEquals(self.q.waveband, "Millimeter")
        self.q.waveband = "infrared"
        self.assertEquals(self.q.waveband, "Infrared")
        self.q.waveband = "ir"
        self.assertEquals(self.q.waveband, "Infrared")
        self.q.waveband = "optical"
        self.assertEquals(self.q.waveband, "Optical")
        self.q.waveband = "uv"
        self.assertEquals(self.q.waveband, "UV")
        self.q.waveband = "UV"
        self.assertEquals(self.q.waveband, "UV")
        self.q.waveband = "euv"
        self.assertEquals(self.q.waveband, "EUV")
        self.q.waveband = "x-ray"
        self.assertEquals(self.q.waveband, "X-ray")
        self.q.waveband = "gamma-ray"
        self.assertEquals(self.q.waveband, "Gamma-ray")

        try:
            self.q.waveband = "blob"
            self.fail("Failed to reject unrecognized waveband")
        except ValueError:
            pass

    def testServicetype(self):
        self.testCtor()
        self.assert_(self.q.servicetype is None)
        self.q.servicetype = "catalog"
        self.assert_(self.q.servicetype is not None)
        self.assertEquals(self.q.servicetype, "catalog")

        del self.q.servicetype
        self.assert_(self.q.servicetype is None)

        self.q.servicetype = "scs"
        self.assertEquals(self.q.servicetype, "scs")
        self.q.servicetype = "ssa"
        self.q.servicetype = "conesearch"
        self.q.servicetype = "Conesearch"
        self.q.servicetype = "table"
        self.q.servicetype = "image"
        self.q.servicetype = "sia"
        self.q.servicetype = "spectrum"
        self.q.servicetype = "spectra"
        self.q.servicetype = "ssa"
        self.q.servicetype = "ssap"
        self.q.servicetype = "line"
        self.q.servicetype = "sla"
        self.q.servicetype = "slap"
        self.q.servicetype = "simpleImageAccess"
        self.q.servicetype = "SimpleImageAccess"
        self.q.servicetype = "simpleSpectralAccess"
        self.q.servicetype = "SimpleSpectralAccess"

        try:
            self.q.servicetype = "SimpleGooberAccess"
            self.fail("failed to reject unrecognized servicetype")
        except ValueError:
            pass
        
    def testOrKeywords(self):
        self.testCtor()
        self.assert_(self.q.will_or_keywords())
        self.q.or_keywords(False)
        self.assert_(not self.q.will_or_keywords())
        self.q.or_keywords(True)
        self.assert_(self.q.will_or_keywords())

    def testKeywords(self):
        self.testCtor()
        self.assertEquals(self.q.keywords, [])

        self.q.addkeywords("galaxy")
        self.assertEquals(self.q.keywords, ["galaxy"])

        self.q.clearkeywords()
        self.assertEquals(self.q.keywords, [])
        
        self.q.addkeywords("AGN")
        self.assertEquals(self.q.keywords, ["AGN"])
        self.q.addkeywords("galaxy")
        self.assertEquals(self.q.keywords, ["AGN", "galaxy"])
        self.q.addkeywords("dwarf companion")
        self.assertEquals(self.q.keywords, ["AGN", "galaxy", "dwarf companion"])
        self.q.addkeywords("HI velocities".split())
        self.assertEquals(self.q.keywords, 
                       ["AGN", "galaxy", "dwarf companion", "HI", "velocities"])

        self.q.removekeywords("HI galaxy".split())
        self.assertEquals(self.q.keywords, 
                          ["AGN", "dwarf companion", "velocities"])

    def testPredicates(self):
        self.testCtor()
        self.assertEquals(self.q.predicates, [])
        
        self.q.addpredicate("Identifier like 'ivo://ncsa.%'")
        self.assertEquals(self.q.predicates, ["Identifier like 'ivo://ncsa.%'"])
        self.q.addpredicate("publisher like '%nrao%'")
        self.assertEquals(self.q.predicates, 
                          ["Identifier like 'ivo://ncsa.%'",
                           "publisher like '%nrao%'"])

        self.q.removepredicate("Identifier like 'ivo://ncsa.%'")
        self.assertEquals(self.q.predicates, ["publisher like '%nrao%'"])

        self.q.clearpredicates()
        self.assertEquals(self.q.predicates, [])

        try:
            self.q.predicates = "Identifier like 'ivo://ncsa.%'"
            self.fail("predicates property is not read-only")
        except AttributeError:
            pass

        self.q.addpredicate("Identifier like 'ivo://ncsa.%'")
        self.q.predicates[0] = "publisherid like 'ivo://ncsa.%'"
        self.assertEquals(self.q.predicates, ["Identifier like 'ivo://ncsa.%'"])

    def testKeywordsToPred(self):
        kws = "gal AGN"
        self.testCtor()

        pat = "(title LIKE '%{t}%' OR shortName LIKE '%{t}%' OR " + \
              "identifier LIKE '%{t}%' OR " + \
              "[content/subject] LIKE '%{t}%' OR "+\
              "[curation/publisher] LIKE '%{t}%' OR " + \
              "[content/description] LIKE '%{t}%')"

        pred = self.q.keywords_to_predicate([kws], True)
        self.assertEquals(pred, pat.format(**{"t": kws}))

        kws = kws.split()
        pred = self.q.keywords_to_predicate(kws[0:1], False)
        self.assertEquals(pred, pat.format(**{"t": kws[0]}))

        pred = self.q.keywords_to_predicate(kws, True)
        self.assertEquals(pred, 
                          (pat.format(**{"t": kws[0]})) + " OR " + 
                          (pat.format(**{"t": kws[1]})))

        pred = self.q.keywords_to_predicate(kws, False)
        self.assertEquals(pred, 
                          (pat.format(**{"t": kws[0]})) + " AND " + 
                          (pat.format(**{"t": kws[1]})))


    def testCreateURL(self):
        baseurl = reg.RegistryService.STSCI_REGISTRY_BASEURL + \
            "VOTCapBandPredOpt?VOTStyleOption=2&"

        self.testCtor()
        self.q.waveband = "ir"
        qurl = self.q.getqueryurl()
        self.assert_(qurl.startswith(baseurl))
        self.assert_("&waveband=Infrared" in qurl)

        self.q.servicetype = "image"
        qurl = self.q.getqueryurl()
        self.assert_("&waveband=Infrared" in qurl)
        self.assert_("&capability=SimpleImageAccess" in qurl)
        self.assert_(qurl.endswith("&predicate="))

        self.q.addpredicate("publisher like '%nrao%'")
        qurl = self.q.getqueryurl()
        self.assert_("&predicate=%28publisher+like+%27%25nrao%25%27%29" in qurl,
                     "unexpected predicate: " + qurl)
        self.q.addpredicate("Identifier like 'ivo%'")
        qurl = self.q.getqueryurl()
        self.assert_("&predicate=%28publisher+like+%27%25nrao%25%27%29+AND+%28Identifier+like+%27ivo%25%27%29" in qurl,
                     "unexpected predicate: " + qurl)
        self.q.clearpredicates()
        qurl = self.q.getqueryurl()
        self.assert_(qurl.endswith("&predicate="))

        # test keywords; not that we tested the pre-URL-encoding of the keyword
        # constraints in testKeywordsToPred()
        self.q.addkeywords(["galaxy", "AGN"])
        qurl = self.q.getqueryurl()
        self.assert_("&waveband=Infrared" in qurl)
        self.assert_("&capability=SimpleImageAccess" in qurl)
        self.assert_("&predicate=1" not in qurl)
        for kw in "AGN galaxy".split():
            for col in ["title", "shortName", "identifier", 
                        "%5Bcontent%2Fsubject%5D", "%5Bcuration%2Fpublisher%5D", 
                        "%5Bcontent%2Fdescription%5D"]:
                constraint = col + "+LIKE+%27%25" + kw + "%25%27"
                self.assert_(constraint in qurl, 
                         "Missing {0} constraint:\n{1}".format(constraint,qurl))
        self.assert_("+OR+shortName+" in qurl)
        self.assert_("+OR+%28title+" in qurl,
                     "unexpected predicate: " + qurl)
        self.q.or_keywords(False)
        qurl = self.q.getqueryurl()
        self.assert_("+AND+%28title+" in qurl)

        self.q.addpredicate("publisher like '%nrao%'")
        qurl = self.q.getqueryurl()
        self.assert_("&predicate=%28publisher+like+%27%25nrao%25%27%29+AND+%28" 
                     in qurl,
                     "unexpected predicate: " + qurl)

class RegResultsTest(unittest.TestCase):

    def setUp(self):
        # load a canned result file
        resultfile = get_pkg_data_filename(regresultfile)
        self.tbl = votableparse(resultfile)

    def testCtor(self):
        self.r = reg.RegistryResults(self.tbl)
        self.assert_(self.r.votable is not None)
        self.assertEquals(self.r.nrecs, 4)

    def testGetValue(self):
        self.testCtor()
        v = self.r.getvalue("shortName", 0)
        if sys.version_info[0] >= 3:
            self.assert_(isinstance(v, bytes))
        else:
            self.assert_(isinstance(v, str))
        self.assertEquals(v, b"J/MNRAS/333/100 [1]")

        v = self.r.getvalue("subject", 0)
        self.assert_(isinstance(v, tuple))
        self.assertEquals(len(v), 4)
        if sys.version_info[0] >= 3:
            self.assert_(isinstance(v[0], bytes))
        else:
            self.assert_(isinstance(v[0], str))
        self.assertEquals(v[0], b"AGN")
        self.assertEquals(v[1], b"Galaxies")
        self.assertEquals(v[3], b"Spectroscopy")

    def testListVal(self):
        self.testCtor()
        self.assert_(isinstance(self.r.getvalue("subject", 0), tuple))
        self.assert_(isinstance(self.r.getvalue("waveband", 0), tuple))
        self.assert_(isinstance(self.r.getvalue("contentLevel", 0), tuple))
        self.assert_(isinstance(self.r.getvalue("type", 0), tuple))

    def testGetRecord(self):
        self.testCtor()
        for i in xrange(4):
            rec = self.r.getrecord(0)
            self.assert_(isinstance(rec, reg.SimpleResource))
        

class SimpleResTest(unittest.TestCase):

    def setUp(self):
        resultfile = get_pkg_data_filename(regresultfile)
        self.tbl = votableparse(resultfile)
        self.result =  reg.RegistryResults(self.tbl)
        self.setrec(0)

    def setrec(self, i):
        self.r = self.result.getrecord(i)

    def testArbitraryCol(self):
        self.setrec(0)
        self.assert_(self.r["description"].startswith(b"We use redshift determinations and spectral"))

    def testAttr(self):
        self.assertEquals(self.r.shortname, b"J/MNRAS/333/100 [1]")
        self.assertEquals(self.r.title, 
                          b"Radio galaxies in the 2dFGRS (Magliocchetti+, 2002)")
        self.assertEquals(self.r.ivoid, b"ivo://CDS.VizieR/J/MNRAS/333/100#1")
        self.assertEquals(self.r.accessurl, 
           "http://vizier.u-strasbg.fr/cgi-bin/VizieR-2?-source=J/MNRAS/333/100")
        self.assertEquals(self.r.publisher, b"CDS")
        self.assertEquals(self.r.tags, b"Web Page")

        # pdb.set_trace()
        self.assert_(isinstance(self.r.subject, tuple))
        self.assertEquals(len(self.r.subject), 4)
        self.assertEquals(self.r.subject[0], b"AGN")
        self.assertEquals(self.r.subject[1], b"Galaxies")
        self.assertEquals(self.r.subject[3], b"Spectroscopy")

        self.assertEquals(self.r.type[0], b"Catalog")
        self.assertEquals(self.r["interfaceClass"], b"WebBrowser")
        self.assertEquals(self.r.standardid, b"")
        self.assertEquals(self.r.capability, b"")

    def testListVal(self):
        self.assert_(isinstance(self.r.subject, tuple))
        self.assert_(isinstance(self.r.waveband, tuple))
        self.assert_(isinstance(self.r.type, tuple))
        self.assert_(isinstance(self.r.contentlevel, tuple))

    def testCap(self):
        self.setrec(2)
        self.assertEquals(self.r.tags, b"Catalog")
        self.assertEquals(self.r.type[0], b"Catalog")
        self.assertEquals(self.r.standardid, b"ivo://ivoa.net/std/ConeSearch")
        self.assertEquals(self.r.capability, b"ConeSearch")

        self.setrec(3)
        self.assertEquals(self.r.tags, b"Images")
        self.assertEquals(self.r.type[0], b"Archive")
        self.assertEquals(self.r.standardid, b"ivo://ivoa.net/std/SIA")
        self.assertEquals(self.r.capability, b"SimpleImageAccess")







class RegExecuteTest(unittest.TestCase):
    pass



__all__ = "RegServiceTest RegQueryTest RegResultsTest SimpleResTest RegExecuteTest".split()
def suite():
    tests = []
    for t in __all__:
        tests.append(unittest.makeSuite(globals()[t]))
    return unittest.TestSuite(tests)

if __name__ == "__main__":
    unittest.main()
