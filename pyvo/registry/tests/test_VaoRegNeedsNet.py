#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.registry.vao module requiring network access
"""
from __future__ import print_function, division

import os, sys, shutil, re, imp
import unittest, pdb

from ...dal import query as dalq
from .. import vao as reg
# from astropy.io.vo import parse as votableparse
from astropy.io.votable.tree import VOTableFile
from astropy.tests.helper import pytest, remote_data

@remote_data
class RegExecuteTest(unittest.TestCase):

    def testExecuteKW(self):
        q = reg.RegistryQuery()
        q.addkeywords("alfalfa")
        # pdb.set_trace()
        r = q.execute()
        s = r.size
        self.assert_(s > 0)

        # confirm the AND's ability to reduce the number of results
        q.addkeywords("Huang")
        r = q.execute()
        self.assert_(r.size < s)

    def testExecuteSvc(self):
        q = reg.RegistryQuery()
        # pdb.set_trace()
        q.servicetype = "sia"
        r = q.execute()
        self.assert_(r.size > 0)

        q.servicetype = "ssa"
        # print(q.getqueryurl())
        r = q.execute()
        self.assert_(r.size > 0)

    def testExecuteWave(self):
        q = reg.RegistryQuery()
        # pdb.set_trace()
        q.waveband = "millimeter"
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
        if sys.version_info[0] >= 3:
            self.assert_(isinstance(x, bytes))
        else:
            self.assert_(isinstance(x, str))
        self.assert_(x.startswith(b"<?xml"))

@remote_data
class RegResolveTest(unittest.TestCase):

    def testResolve(self):
        service = reg.RegistryService()
        #        r = service.resolve("ivo://CDS.VizieR/J/MNRAS/333/100#1")
        r = service.resolve("ivo://CDS.VizieR/J/MNRAS/333/100")
        self.assert_(isinstance(r, reg.SimpleResource))
        self.assertEquals(r.identifier, b"ivo://CDS.VizieR/J/MNRAS/333/100#1")
        self.assertEquals(r.shortname, b"J/MNRAS/333/100 [1]")
        self.assertEquals(r.title, 
                          b"Radio galaxies in the 2dFGRS (Magliocchetti+, 2002)")

__all__ = "RegExecuteTest RegResolveTest".split()
def suite():
    tests = []
    for t in __all__:
        tests.append(unittest.makeSuite(globals()[t]))
    return unittest.TestSuite(tests)

if __name__ == "__main__":
    unittest.main()


