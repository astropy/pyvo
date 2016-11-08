#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.nameresolver.sesame requiring the network
"""
from __future__ import print_function, division

import os, sys, shutil, re, imp
import unittest, pdb

from .. import sesame
import xml.etree.ElementTree as ET
from astropy.tests.helper import pytest, remote_data

mirrors = ["cfa", "cds"]
default_mirror = "cds"

if default_mirror in mirrors:
    mirrors.remove(default_mirror)
alt_mirror = mirrors[0]
sesame.set_default_endpoint(default_mirror)

do_remote = False

@remote_data
class SesameQueryTest(unittest.TestCase):

    def testExecuteStream(self):
        q = sesame.SesameQuery()
        q.names = ["ngc4258", "goob's star", "m51"]
        strm = q.execute_stream()
        doc = ET.parse(strm)
        strm.close()
        self.assertEquals("Sesame", doc.getroot().tag)

        strm = q.execute_stream(astext=True)
        doc = ET.parse(strm)
        strm.close()
        self.assertEquals("Sesame", doc.getroot().tag)

        strm = q.execute_stream(format="pc")
        lines = []
        for line in strm:
            lines.append(line)
        strm.close()
        self.assertTrue(lines[0].startswith(b'#'), 
                        b"unexpected first line: " + lines[0])
        self.assertTrue(lines[5].startswith(b'%'), 
                        b"unexpected mid-line: " + lines[5])

        q.dbs = "GB"
        self.assertRaises(sesame.DALQueryError, q.execute_stream)
        strm = q.execute_stream(lax=True)
        strm.close()

        del q.dbs
        self.assertEquals("", q.dbs)
        q.opts = "bo"
        self.assertRaises(sesame.DALQueryError, q.execute_stream)
        strm = q.execute_stream(lax=True)
        strm.close()

    def testExecute(self):
        q = sesame.SesameQuery()
        q.names = ["ngc4258"]

        r = q.execute()
        self.assertTrue(isinstance(r, list))
        self.assertEquals(1, len(r))
        
        q.names = ["ngc4258", "goob's star", "m51"]
        r = q.execute()
        self.assertTrue(isinstance(r, list))
        self.assertEquals(3, len(r))

        target = r[0]
        self.assertEquals(1, len(target.responses))
        self.assertTrue(target.resolved)
        odata = target.responses[0]
        self.assertEquals("M 106", odata.oname)
        odata = target.according_to("sim")
        self.assertTrue(odata is not None)
        self.assertEquals("M 106", odata.oname)
        
        target = r[1]
        self.assertEquals(0, len(target.responses))
        self.assertFalse(target.resolved)
        self.assertTrue(target.name.startswith("goob's"))
        odata = target.according_to("sim")
        self.assertTrue(odata is None)

        q.useDatabases("Simbad", "Vizier", "all")
        r = q.execute()
        self.assertTrue(isinstance(r, list))
        self.assertEquals(3, len(r))

        # Note: Vizier, NED resolvers appear no longer to be working from CDS
        target = r[0]
        # self.assertEquals(2, len(target.responses))
        self.assertEquals(1, len(target.responses))
        self.assertTrue(target.resolved)
        odata = target.according_to("sim")
        self.assertTrue(odata is not None)
        self.assertEquals("M 106", odata.oname)
        odata = target.according_to("viz")
        self.assertTrue(odata is None)
        # self.assertTrue(odata is not None)
        # self.assertEquals("{NGC} 4258", odata.oname)


@remote_data
class ResolveTest(unittest.TestCase):

    def testDefault(self):
        odata = sesame.resolve("NGC4258")
        self.assertTrue(odata is not None)
        self.assertFalse(isinstance(odata, list))
        self.assertTrue(odata.resolver_name.startswith("Sc=Simbad"))
        self.assertEquals("M 106", odata.oname)
        self.assertTrue("otype" in odata.keys())

        odata = sesame.resolve(["NGC4258", "M51"])
        self.assertTrue(odata is not None)
        self.assertTrue(isinstance(odata, list))
        self.assertTrue(odata[1].resolver_name.startswith("Sc=Simbad"))
        self.assertEquals("M 106", odata[0].oname)
        self.assertEquals("M  51", odata[1].oname)
        self.assertTrue("otype" in odata[0].keys())
        self.assertTrue("otype" in odata[1].keys())

    # CDS doesn't support NED and Vizier anymore?
#    def testDb(self):
#        odata = sesame.resolve("NGC4258", "NED")
#        self.assertTrue(odata is not None)
#        self.assertFalse(isinstance(odata, list))
#        self.assertTrue(odata.resolver_name.startswith("N=NED"))
#        self.assertEquals("MESSIER 106", odata.oname)
#        self.assertTrue("MType" in odata.keys())
#        
#        odata = sesame.resolve(["NGC4258", "M51"], "NED")
#        self.assertTrue(odata is not None)
#        self.assertTrue(isinstance(odata, list))
#        self.assertTrue(odata[1].resolver_name.startswith("N=NED"))
#        self.assertEquals("MESSIER 106", odata[0].oname)
#        self.assertEquals("MESSIER 051", odata[1].oname)
#        self.assertTrue("nrefs" in odata[0].keys())
#        self.assertTrue("nrefs" in odata[1].keys())
#
#        odata = sesame.resolve("NGC4258", "Vizier")
#        self.assertTrue(odata is not None)
#        self.assertFalse(isinstance(odata, list))
#        self.assertTrue(odata.resolver_name.startswith("V=VizieR"))
#        self.assertEquals("{NGC} 4258", odata.oname)
#        self.assertTrue("jpos" in odata.keys())
        
    def testInclude(self):
        odata = sesame.resolve("NGC4258", include=" aliases fluxes")
        self.assertTrue(odata is not None)
        self.assertFalse(isinstance(odata, list))
        self.assertTrue("alias" in odata.keys())
        self.assertTrue(len(odata.aliases) > 0)

        odata = sesame.resolve("NGC4258", include=["fluxes", "aliases"])
        self.assertTrue(odata is not None)
        self.assertFalse(isinstance(odata, list))
        self.assertTrue("alias" in odata.keys())
        self.assertTrue(len(odata.aliases) > 0)

        odata = sesame.resolve("NGC4258", include="aliases ")
        self.assertTrue(odata is not None)
        self.assertFalse(isinstance(odata, list))
        self.assertTrue("alias" in odata.keys())
        self.assertTrue(len(odata.aliases) > 0)

    def testMirror(self):
        odata = sesame.resolve("NGC4258", mirror="cds")
        self.assertTrue(odata is not None)
        self.assertTrue(odata.resolver_name.startswith("Sc=Simbad"))
        self.assertEquals("M 106", odata.oname)
        self.assertTrue("otype" in odata.keys())

        odata = sesame.resolve("NGC4258", mirror="cfa")
        self.assertTrue(odata is not None)
        self.assertTrue(odata.resolver_name.startswith("Sc=Simbad"))
        self.assertEquals("M 106", odata.oname)
        self.assertTrue("otype" in odata.keys())

        self.assertRaises(LookupError, sesame.resolve, "NGC4258", mirror="ncsa")

@remote_data
class Object2posTest(unittest.TestCase):

    def testDefault(self):
        pos = sesame.object2pos("NGC4258")
        self.assertTrue(pos is not None)
        self.assertFalse(isinstance(pos, list))
        self.assertTrue(isinstance(pos, tuple))
        self.assertEquals(2, len(pos))
        self.assertTrue(all(map(lambda p: isinstance(p,float), pos)))
        self.assertAlmostEquals(184.74008333, pos[0])
        self.assertAlmostEquals(47.30371944, pos[1])

        pos = sesame.object2pos(["NGC4258", "M51"])
        self.assertTrue(pos is not None)
        self.assertTrue(isinstance(pos, list))
        self.assertTrue(isinstance(pos[0], tuple))
        self.assertTrue(isinstance(pos[1], tuple))
        self.assertEquals(2, len(pos[1]))
        self.assertAlmostEquals(184.74008333, pos[0][0])
        self.assertAlmostEquals(47.30371944, pos[0][1])

        pos = sesame.object2pos(["NGC4258"])
        self.assertTrue(pos is not None)
        self.assertTrue(isinstance(pos, list))

    def testDb(self):
        pos = sesame.object2pos("NGC4258", "V")
        self.assertTrue(pos is not None)
        self.assertAlmostEquals(184.73, pos[0], places=2)
        self.assertAlmostEquals(47.31, pos[1], places=2)

    def testMirror(self):
        pos = sesame.object2pos("NGC4258", mirror="cds")
        self.assertTrue(pos is not None)
        self.assertFalse(isinstance(pos, list))
        self.assertTrue(isinstance(pos, tuple))
        self.assertEquals(2, len(pos))
        self.assertTrue(all(map(lambda p: isinstance(p,float), pos)))
        self.assertAlmostEquals(184.74008333, pos[0])
        self.assertAlmostEquals(47.30371944, pos[1])

        pos = sesame.object2pos("NGC4258", mirror="cfa")
        self.assertTrue(pos is not None)
        self.assertFalse(isinstance(pos, list))
        self.assertTrue(isinstance(pos, tuple))
        self.assertEquals(2, len(pos))
        self.assertTrue(all(map(lambda p: isinstance(p,float), pos)))
        self.assertAlmostEquals(184.74008333, pos[0])
        self.assertAlmostEquals(47.30371944, pos[1])

        self.assertRaises(LookupError, sesame.object2pos, "NGC4258", 
                          mirror="ncsa")

@remote_data
class Object2sexaposTest(unittest.TestCase):

    def testDefault(self):
        pos = sesame.object2sexapos("NGC4258")
        self.assertTrue(pos is not None)
        self.assertFalse(isinstance(pos, list))
        self.assertTrue(isinstance(pos, str))
        self.assertEquals("12:18:57.61 +47:18:13.3", pos)

        pos = sesame.object2sexapos(["NGC4258", "M51"])
        self.assertTrue(pos is not None)
        self.assertTrue(isinstance(pos, list))
        self.assertEquals(2, len(pos))
        self.assertTrue(isinstance(pos[0], str))
        self.assertTrue(isinstance(pos[1], str))
        self.assertEquals("12:18:57.61 +47:18:13.3", pos[0])

        pos = sesame.object2sexapos(["NGC4258"])
        self.assertTrue(pos is not None)
        self.assertTrue(isinstance(pos, list))
        self.assertEquals(1, len(pos))
        self.assertTrue(isinstance(pos[0], str))
        self.assertEquals("12:18:57.61 +47:18:13.3", pos[0])

    def testDb(self):
        pos = sesame.object2sexapos("NGC4258", "V")
        self.assertTrue(pos is not None)
        self.assertEquals("12:18.9     +47:19", pos)




__all__ = "SesameQueryTest".split()
def suite():
    tests = []
    for t in __all__:
        tests.append(unittest.makeSuite(globals()[t]))
    return unittest.TestSuite(tests)

if __name__ == "__main__":
    unittest.main()
