#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.dal.sia
"""
from __future__ import print_function, division

import os, sys, shutil, re, imp
import unittest, pdb
from urllib2 import URLError, HTTPError

import pyvo.dal.query as dalq
import pyvo.dal.sia as sia
# from astropy.io.vo import parse as votableparse
from astropy.io.votable.tree import VOTableFile
from astropy.io.votable.tree import VOTableFile
from astropy.tests.helper import pytest, remote_data

neat = "http://skyview.gsfc.nasa.gov/cgi-bin/vo/sia.pl?survey=neat&"

@remote_data
class NeatSIAExecuteTest(unittest.TestCase):

    imfile = "testimg.fits"

    def setUp(self):
        self.tearDown()

    def tearDown(self):
        if os.path.exists(self.imfile):
            # pass
            os.remove(self.imfile)

    def testExecute(self):
        q = sia.SIAQuery(neat)
        q.pos = (0, 0)
        q.size = (1.0, 1.0)
        q.format = "all"
        q.setparam("NAXIS", (75, 75))
        results = q.execute()
        self.assert_(isinstance(results, sia.SIAResults))
        self.assertEquals(results.nrecs, 5)

        rec = results.getrecord(0)
        self.assertEquals(rec.naxis, (75, 75))

    def testSearch(self):
        srv = sia.SIAService(neat)
        results = srv.search(pos=(0,0), size=(1.0,1.0))
        self.assert_(isinstance(results, sia.SIAResults))
        self.assertEquals(results.nrecs, 5)

    def testSia(self):
        results = sia.search(neat, pos=(0,0), size=(0.25,0.25))
        self.assert_(isinstance(results, sia.SIAResults))
        self.assertEquals(results.nrecs, 5)

        rec = results.getrecord(0)
        self.assertEquals(rec.ra, 0.0)
        self.assertEquals(rec.dec, 0.0)
        self.assertEquals(rec.title, b"neat")
        self.assert_(rec.dateobs is None)
        self.assertEquals(rec.naxes, 2)
        self.assertEquals(rec.naxis, (300, 300))
        self.assert_(rec.instr is None)
        self.assert_(rec.format is not None)
        # self.assertEquals(rec.acref, self.acref)

        qurl = rec.getdataurl()
        self.assert_(qurl is not None and len(qurl) > 0)
        self.assert_(not os.path.exists(self.imfile))
        # print(qurl)
        rec.cachedataset(self.imfile)
        self.assert_(os.path.exists(self.imfile))

        if rec.format == b"image/fits":
            with open(self.imfile) as fits:
                hdr = fits.read(20)
                self.assert_(hdr.startswith("SIMPLE  ="), "Not a FITS image?")
        
        

__all__ = "NeatSIAExecuteTest".split()
def suite():
    tests = []
    for t in __all__:
        tests.append(unittest.makeSuite(globals()[t]))
    return unittest.TestSuite(tests)

if __name__ == "__main__":
    unittest.main()

