#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.nameresolver.sesame
"""
from __future__ import print_function, division

import os, sys, shutil, re, imp
import unittest

from .. import sesame
import xml.etree.ElementTree as ET
from astropy.utils.data import get_pkg_data_filename

resultfile = "data/sesame.xml"

xmldecl = "<?xml version=\"1.0\"?>"

class DocQuantityTest(unittest.TestCase):

    xmldecl = "<?xml version=\"1.0\"?>"

    def makeQuantXML(self, tag, include="eqr"):
        out = "{0}<{1}><v>447.89000</v>".format(self.xmldecl, tag)
        if 'e' in include:
            out += "<e>2.99793</e>"
        if 'q' in include:
            out += "<q>A</q>"
        if 'r' in include:
            out += "<r>1991RC3.9.C...0000d</r>"
        out += "</{0}>".format(tag)
        return out

    def makeQuantEl(self, tag="Vel", include="eqr"):
        xml = self.makeQuantXML(tag, include)
        return ET.fromstring(xml)

    def testUnit(self):
        q = sesame.DocQuantity(self.makeQuantEl("Vel", include=""))
        self.assertEquals("km/s", q.unit)
        q = sesame.DocQuantity(self.makeQuantEl("pm", include=""))
        self.assertEquals("mas/yr", q.unit)
        q = sesame.DocQuantity(self.makeQuantEl("plx", include=""))
        self.assertEquals("mas", q.unit)
        q = sesame.DocQuantity(self.makeQuantEl("z", include=""))
        self.assertEquals("", q.unit)
        q = sesame.DocQuantity(self.makeQuantEl("mag", include=""))
        self.assertEquals("", q.unit)

    def testToString(self):
        q = sesame.DocQuantity(self.makeQuantEl())
        self.assertEquals("447.89 km/s", q.to_string(False))
        self.assertEquals("447.89 +/- 2.99793 km/s", q.to_string(True))
        self.assertEquals("447.89 +/- 2.99793 km/s", str(q))

        # pdb.set_trace()
        self.assertTrue(re.match(r'quant\((\S+,\s){4}\S+\)', repr(q)) is not None)

        q = sesame.DocQuantity(self.makeQuantEl(include=""))
        self.assertEquals("447.89 km/s", q.to_string(False))
        self.assertEquals("447.89 km/s", q.to_string(True))
        self.assertEquals("447.89 km/s", str(q))

        self.assertTrue(re.match(r'quant\((\S+,\s){4}\S+\)', repr(q)) is not None)

    def testCtor(self):
        q = sesame.DocQuantity(self.makeQuantEl())
        self.assertAlmostEquals(447.89, q.val)
        self.assertAlmostEquals(2.997930, q.error)
        self.assertEquals("km/s", q.unit)
        self.assertEquals("A", q.qual)
        self.assertEquals("1991RC3.9.C...0000d", q.ref)

        q = sesame.DocQuantity(self.makeQuantEl(include=""))
        self.assertAlmostEquals(447.89, q.val)
        self.assertTrue(q.error is None)
        self.assertEquals("km/s", q.unit)
        self.assertTrue(q.qual is None)
        self.assertTrue(q.ref is None)

        q = sesame.DocQuantity(self.makeQuantEl(include="e"))
        self.assertAlmostEquals(447.89, q.val)
        self.assertAlmostEquals(2.997930, q.error)
        self.assertEquals("km/s", q.unit)
        self.assertTrue(q.qual is None)
        self.assertTrue(q.ref is None)

        q = sesame.DocQuantity(self.makeQuantEl(include="eq"))
        self.assertAlmostEquals(447.89, q.val)
        self.assertAlmostEquals(2.997930, q.error)
        self.assertEquals("km/s", q.unit)
        self.assertEquals("A", q.qual)
        self.assertTrue(q.ref is None)

        q = sesame.DocQuantity(self.makeQuantEl(include="er"))
        self.assertAlmostEquals(447.89, q.val)
        self.assertAlmostEquals(2.997930, q.error)
        self.assertEquals("km/s", q.unit)
        self.assertTrue(q.qual is None)
        self.assertEquals("1991RC3.9.C...0000d", q.ref)


class ProperMotionTest(unittest.TestCase):

    def makeQuantXML(self, include="eqr"):
        tag = "pm"
        out = "{0}<{1}><v>3.44</v>".format(xmldecl, tag)
        if 'e' in include:
            out += "<e>0.28</e>"
        if 'q' in include:
            out += "<q>A</q>"
        if 'r' in include:
            out += "<r>1991RC3.9.C...0000d</r>"

        out += "<pa>54.18</pa><pmRA>3.1</pmRA>"
        if 'e' in include:
            out += "<epmRA>0.2</epmRA>"
        out += "<pmDE>1.5</pmDE>"
        if 'e' in include:
            out += "<epmDE>0.2</epmDE>"

        out += "</{0}>".format(tag)
        return out

    def makeQuantEl(self, include="eqr"):
        xml = self.makeQuantXML(include)
        return ET.fromstring(xml)

    def testToString(self):
        q = sesame.ProperMotion(self.makeQuantEl())
        self.assertEquals("3.44 mas/yr", q.to_string(False))
        self.assertEquals("3.44 +/- 0.28 mas/yr", q.to_string(True))
        self.assertEquals("3.44 +/- 0.28 mas/yr", str(q))

        # pdb.set_trace()
        self.assertTrue(re.match(r'pm\((\S+,\s){9}\S+\)', repr(q)) is not None)

        q = sesame.ProperMotion(self.makeQuantEl(include=""))
        self.assertEquals("3.44 mas/yr", q.to_string(False))
        self.assertEquals("3.44 mas/yr", q.to_string(True))
        self.assertEquals("3.44 mas/yr", str(q))

        self.assertTrue(re.match(r'pm\((\S+,\s){9}\S+\)', repr(q)) is not None)

    def testCtor(self):
        q = sesame.ProperMotion(self.makeQuantEl())
        self.assertAlmostEquals(3.44, q.val)
        self.assertAlmostEquals(0.28, q.error)
        self.assertAlmostEquals(54.18, q.pa)
        self.assertAlmostEquals(3.1, q.val_ra)
        self.assertAlmostEquals(1.5, q.val_dec)
        self.assertAlmostEquals(0.2, q.error_ra)
        self.assertAlmostEquals(0.2, q.error_dec)
        self.assertEquals("mas/yr", q.unit)
        self.assertEquals("A", q.qual)
        self.assertEquals("1991RC3.9.C...0000d", q.ref)

        q = sesame.ProperMotion(self.makeQuantEl(include=""))
        self.assertAlmostEquals(3.44, q.val)
        self.assertAlmostEquals(54.18, q.pa)
        self.assertAlmostEquals(3.1, q.val_ra)
        self.assertAlmostEquals(1.5, q.val_dec)
        self.assertTrue(q.error is None)
        self.assertTrue(q.error_ra is None)
        self.assertTrue(q.error_dec is None)
        self.assertEquals("mas/yr", q.unit)
        self.assertTrue(q.qual is None)
        self.assertTrue(q.ref is None)

        q = sesame.ProperMotion(self.makeQuantEl(include="e"))
        self.assertAlmostEquals(3.44, q.val)
        self.assertAlmostEquals(0.28, q.error)
        self.assertAlmostEquals(54.18, q.pa)
        self.assertAlmostEquals(3.1, q.val_ra)
        self.assertAlmostEquals(1.5, q.val_dec)
        self.assertAlmostEquals(0.2, q.error_ra)
        self.assertAlmostEquals(0.2, q.error_dec)
        self.assertEquals("mas/yr", q.unit)
        self.assertTrue(q.qual is None)
        self.assertTrue(q.ref is None)

        q = sesame.ProperMotion(self.makeQuantEl(include="eq"))
        self.assertAlmostEquals(3.44, q.val)
        self.assertAlmostEquals(0.28, q.error)
        self.assertAlmostEquals(54.18, q.pa)
        self.assertAlmostEquals(3.1, q.val_ra)
        self.assertAlmostEquals(1.5, q.val_dec)
        self.assertAlmostEquals(0.2, q.error_ra)
        self.assertAlmostEquals(0.2, q.error_dec)
        self.assertEquals("mas/yr", q.unit)
        self.assertEquals("A", q.qual)
        self.assertTrue(q.ref is None)

        q = sesame.ProperMotion(self.makeQuantEl(include="r"))
        self.assertAlmostEquals(3.44, q.val)
        self.assertAlmostEquals(54.18, q.pa)
        self.assertAlmostEquals(3.1, q.val_ra)
        self.assertAlmostEquals(1.5, q.val_dec)
        self.assertEquals("mas/yr", q.unit)
        self.assertTrue(q.qual is None)
        self.assertTrue(q.error is None)
        self.assertTrue(q.error_ra is None)
        self.assertTrue(q.error_dec is None)
        self.assertEquals("1991RC3.9.C...0000d", q.ref)

class ObjectDataTest(unittest.TestCase):

    def setUp(self):
        result = get_pkg_data_filename(resultfile)
        self.sesel = ET.parse(result).getroot()

    def selectResolver(self, target, which):
        # pdb.set_trace()
        el = self.sesel.findall("Target")
        el = el[int(target-1)]
        el = el.findall("Resolver")
        return el[int(which-1)]

    def testNotFound(self):
        # pdb.set_trace()
        el = self.selectResolver(2, 1)
        res = sesame.ObjectData(el)
        self.assertFalse(res.success)

        el = self.selectResolver(2, 2)
        res = sesame.ObjectData(el)
        self.assertFalse(res.success)

        el = self.selectResolver(1, 1)
        res = sesame.ObjectData(el)
        self.assertTrue(res.success)

    def testVizier(self):
        el = self.selectResolver(1, 1)
        res = sesame.ObjectData(el)
        self.assertTrue(res.success)
        self.assertTrue(res.fromcache)

        self.assertEquals("V=VizieR (local)", res.resolver_name)
        self.assertEquals("12:18.9     +47:19", res.sexapos)
        self.assertEquals(2, len(res.pos))
        self.assertAlmostEquals(184.73, res.pos[0])
        self.assertAlmostEquals(47.31, res.pos[1])
        self.assertEquals("{NGC} 4258", res.oname)

    def testSimbad(self):
        el = self.selectResolver(1, 2)
        res = sesame.ObjectData(el)
        self.assertTrue(res.success)
        self.assertFalse(res.fromcache)

        self.assertEquals("S=Simbad (CDS, via client/server)", 
                          res.resolver_name)
        self.assertEquals("12:18:57.61 +47:18:13.3", res.sexapos)
        self.assertEquals(2, len(res.pos))
        self.assertAlmostEquals(184.74008333, res.pos[0])
        self.assertAlmostEquals(47.30371944, res.pos[1])
        self.assertEquals("M 106", res.oname)

    def testGet(self):
        el = self.selectResolver(1, 2)
        res = sesame.ObjectData(el)
        self.assertTrue(res.success)
        self.assertEquals("S=Simbad (CDS, via client/server)", 
                          res.resolver_name)

        self.assertEquals("12:18:57.61 +47:18:13.3", res.get('jpos'))
        self.assertEquals("184.74008333", res.get('jradeg'))
        self.assertEquals("47.30371944", res.get('jdedeg'))
        self.assertEquals("M 106", res.get('oname'))
        self.assertEquals("LIN", res.get('otype'))
        self.assertEquals("@609478", res.get('oid'))
        self.assertEquals("2006AJ....131.1163S", res.get('refPos'))
        self.assertEquals("3", res.get('MType'))

        z = res.get('z')
        self.assertTrue(z is not None)
        self.assertEquals("D", z.qual)
        self.assertEquals("2002LEDA.........0P", z.ref)

        aliases = res.get('alias')
        self.assertEquals(35, len(aliases))
        self.assertTrue("Z 1216.5+4735" in aliases)
        self.assertTrue("UGC 7353" in aliases)

        self.assertTrue(res.get('Vel') is None)

    def testGetitem(self):
        el = self.selectResolver(1, 2)
        res = sesame.ObjectData(el)
        self.assertTrue(res.success)
        self.assertEquals("S=Simbad (CDS, via client/server)", 
                          res.resolver_name)

        self.assertEquals("12:18:57.61 +47:18:13.3", res['jpos'])
        self.assertEquals("184.74008333", res['jradeg'])
        self.assertEquals("47.30371944", res['jdedeg'])
        self.assertEquals("M 106", res['oname'])
        self.assertEquals("LIN", res['otype'])
        self.assertEquals("@609478", res['oid'])
        self.assertEquals("2006AJ....131.1163S", res['refPos'])
        self.assertEquals("3", res['MType'])

        z = res['z']
        self.assertTrue(z is not None)
        self.assertTrue(isinstance(z, sesame.DocQuantity))
        self.assertEquals("D", z.qual)
        self.assertEquals("2002LEDA.........0P", z.ref)

        aliases = res['alias']
        self.assertEquals(35, len(aliases))
        self.assertTrue("Z 1216.5+4735" in aliases)
        self.assertTrue("UGC 7353" in aliases)

    def testKeys(self):
        el = self.selectResolver(1, 1)
        res = sesame.ObjectData(el)
        self.assertTrue(res.success)
        self.assertTrue(res.resolver_name.startswith("V=VizieR"), 
                        "Not matched: " + res.resolver_name)
        keys = res.keys()
        self.assertTrue("jpos" in keys)
        self.assertTrue("oname" in keys)
        self.assertTrue("jradeg" in keys)
        self.assertTrue("jdedeg" in keys)
        self.assertEquals(5, len(keys))

        el = self.selectResolver(1, 3)
        res = sesame.ObjectData(el)
        self.assertTrue(res.success)
        self.assertTrue(res.resolver_name.startswith("N=NED"), 
                        "Not matched: " + res.resolver_name)
        keys = res.keys()
        self.assertTrue("jpos" in keys)
        self.assertTrue("oname" in keys)
        self.assertTrue("jradeg" in keys)
        self.assertTrue("jdedeg" in keys)
        self.assertTrue("MType" in keys)
        self.assertEquals(12, len(keys))


class TargetTest(unittest.TestCase):

    def setUp(self):
        result = get_pkg_data_filename(resultfile)
        self.sesel = ET.parse(result).getroot()

    def selectTarget(self, which):
        # pdb.set_trace()
        el = self.sesel.findall("Target")
        return el[int(which-1)]

    def testProp(self):
        target = sesame.Target(self.selectTarget(1))

        self.assertEquals("ngc 4258", target.name)
        self.assertEquals("VSNA", target.dbcodes)
        self.assertEquals(3, len(target.responses))

        for res in target.responses:
            self.assertTrue(isinstance(res, sesame.ObjectData))

    def testResponses(self):
        for t in xrange(1,4):
            target = sesame.Target(self.selectTarget(t))

            for res in target.responses:
                if t == 2:
                    self.assertFalse(res.success)
                else:
                    self.assertTrue(res.success)

    def testAccordingTo(self):
        target = sesame.Target(self.selectTarget(1))

        res = target.according_to("sim")
        self.assertTrue(res is not None)
        self.assertEquals("M 106", res.oname)

        res = target.according_to("viz")
        self.assertTrue(res is not None)
        self.assertEquals("{NGC} 4258", res.oname)

        res = target.according_to("NED")
        self.assertTrue(res is not None)

        res = target.according_to("goob")
        self.assertTrue(res is None)

        self.assertRaises(LookupError, target.according_to, "")

class SesameQueryTest(unittest.TestCase):

    def setUp(self):
        self.query = sesame.SesameQuery()

    def testCtor(self):
        self.assertEquals(sesame.default_endpoint, self.query.baseurl)
        self.query = sesame.SesameQuery(sesame.endpoints["cfa"])
        self.assertEquals(sesame.endpoints["cfa"], self.query.baseurl)

    def testDbs(self):
        self.assertEquals("", self.query.dbs)
        self.query.dbs = "SV"
        self.assertEquals("SV", self.query.dbs)
        self.query.dbs = "GB"
        self.assertEquals("GB", self.query.dbs)
        del self.query.dbs
        self.assertEquals("", self.query.dbs)

        self.query.useDatabases("Simb", "Vi")
        self.assertEquals("SV", self.query.dbs)

        # pdb.set_trace()
        self.query.useDefaultDatabase()
        self.assertEquals("", self.query.dbs)

    def testGetQueryURL(self):
        self.query.names = "m51"
        self.assertEquals(sesame.default_endpoint + "/-ox?m51", 
                          self.query.getqueryurl())
        self.query.names = "m101 m51".split()
        self.query.opts = 'I'
        self.assertEquals(sesame.default_endpoint +  "/-oxI?m101&m51", 
                          self.query.getqueryurl())
        self.query.dbs = "SN"
        self.assertEquals(sesame.default_endpoint +  "/-oxI/SN?m101&m51", 
                          self.query.getqueryurl())
        self.query.ignorecache = True
        self.assertEquals(sesame.default_endpoint +  "/-oxI/~SN?m101&m51", 
                          self.query.getqueryurl())

        self.assertEquals(sesame.default_endpoint +  "/-oxI/~SN?m101&m51", 
                          self.query.getqueryurl(format='x'))
        self.assertEquals(sesame.default_endpoint +  "/-ox2I/~SN?m101&m51", 
                          self.query.getqueryurl(format='x2'))
        self.assertEquals(sesame.default_endpoint +  "/-oI/~SN?m101&m51", 
                          self.query.getqueryurl(format='pc'))
        self.assertEquals(sesame.default_endpoint +  "/-ox2pI/~SN?m101&m51", 
                          self.query.getqueryurl(format='x2', astext=True))

    def assertRaisesOnQuery(self, msg, format=None):
        self.assertRaises(sesame.DALQueryError, self.query.getqueryurl,
                          format=format)
        self.query.getqueryurl(True)

    def testGetBadQueryURL(self):
        self.assertRaisesOnQuery("Failed to catch lack of source")
        self.query.names = "m51"
        self.query.dbs = "GB"
        self.assertRaisesOnQuery("Failed to catch bad DB codes")
        self.query.dbs = ""
        self.query.opts = "gw"
        self.assertRaisesOnQuery("Failed to catch bad option codes")
        self.query.opts = ""
        self.assertRaisesOnQuery("Failed to catch bad format", "uu")

class EndpointSetTest(unittest.TestCase):

    def testSetDef(self):
        self.assertEquals(sesame.endpoints["cds"], sesame.default_endpoint)

        # pdb.set_trace()
        sesame.set_default_endpoint("cds")
        self.assertEquals(sesame.endpoints["cds"], sesame.default_endpoint)
        sesame.set_default_endpoint("cfa")
        self.assertEquals(sesame.endpoints["cfa"], sesame.default_endpoint)
        


__all__ = "DocQuantityTest ProperMotionTest ObjectDataTest SesameQueryTest EndpointSetTest".split()
def suite():
    tests = []
    for t in __all__:
        tests.append(unittest.makeSuite(globals()[t]))
    return unittest.TestSuite(tests)

if __name__ == "__main__":
    unittest.main()
