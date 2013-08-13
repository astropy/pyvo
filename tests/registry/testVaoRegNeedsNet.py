#!/usr/bin/env python
"""
Tests for pyvo.registry.vao module
"""
import os
import sys
import shutil
import re
import imp
import unittest
import pdb
from urllib2 import URLError, HTTPError

import pyvo.dal.query as dalq
import pyvo.registry.vao as reg
# from astropy.io.vo import parse as votableparse
from astropy.io.votable.tree import VOTableFile


class RegExecuteTest(unittest.TestCase):

    def testExecuteKW(self):
        q = reg.RegistryQuery()
        q.addkeywords("spiral")
        # pdb.set_trace()
        r = q.execute()
        self.assert_(r.size > 0)

        q.addkeywords("galaxies")
        r = q.execute()
        self.assert_(r.size > 0)

    def testExecuteSvc(self):
        q = reg.RegistryQuery()
        # pdb.set_trace()
        q.servicetype = "sia"
        r = q.execute()
        self.assert_(r.size > 0)

        q.servicetype = "conesearch"
        # print q.getqueryurl()
        r = q.execute()
        self.assert_(r.size > 0)

    def testExecuteWave(self):
        q = reg.RegistryQuery()
        # pdb.set_trace()
        q.waveband = "optical"
        r = q.execute()
        self.assert_(r.size > 0)

    def testExecuteVotable(self):
        q = reg.RegistryQuery()
        # pdb.set_trace()
        q.servicetype = "ssa"
        v = q.execute_votable()
        self.assert_(isinstance(v, VOTableFile))
        self.assert_(len(v.resources) > 0)

    def testExecuteStream(self):
        q = reg.RegistryQuery()
        q.servicetype = "ssa"
        s = q.execute_stream()
        self.assert_(hasattr(s, "read"))

    def testExecuteRaw(self):
        q = reg.RegistryQuery()
        q.servicetype = "ssa"
        x = q.execute_raw()
        self.assert_(isinstance(x, str))
        self.assert_(x.startswith("<?xml"))


class RegResolveTest(unittest.TestCase):

    def testResolve(self):
        service = reg.RegistryService()
        # r = service.resolve("ivo://CDS.VizieR/J/MNRAS/333/100#1")
        r = service.resolve("ivo://CDS.VizieR/J/MNRAS/333/100")
        self.assert_(isinstance(r, reg.SimpleResource))
        self.assertEquals(r.identifier, "ivo://CDS.VizieR/J/MNRAS/333/100#1")
        self.assertEquals(r.shortname, "J/MNRAS/333/100 [1]")
        self.assertEquals(r.title,
                          "Radio galaxies in the 2dFGRS (Magliocchetti+, 2002)")

__all__ = "RegExecuteTest RegResolveTest".split()


def suite():
    tests = []
    for t in __all__:
        tests.append(unittest.makeSuite(globals()[t]))
    return unittest.TestSuite(tests)

if __name__ == "__main__":
    unittest.main()
