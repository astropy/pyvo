#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.dal.datalink
"""
from __future__ import (
    absolute_import, division, print_function, unicode_literals)

import os, sys, shutil, re, imp, glob, tempfile, random, time
import unittest, pdb
import os.path

import pyvo as vo
import pyvo.dal.datalink as datalink
# from astropy.io.vo import parse as votableparse
from astropy.io.votable.tree import VOTableFile
from astropy.io.votable import parse as votableparse
from astropy.utils.data import get_pkg_data_filename
from . import testserver

tapresultfile = os.path.join(os.path.dirname(__file__), "data/arihip-tap.xml")
errresultfile = "data/error-tap.xml"
uploadfile = "data/upload-tap.xml"
testserverport = 8084

class DatalinkRunTest(unittest.TestCase):
    ssa_baseurl = "http://localhost:{0}/datalink_ssa?"
    dl_baseurl = "http://localhost:{0}/datalink?"

    @classmethod
    def setup_class(cls):
        cls.srvr = testserver.get_server(testserverport)
        cls.srvr.start()
        time.sleep(0.5)

    @classmethod
    def teardown_class(cls):
        if cls.srvr.is_alive():
            cls.srvr.terminate()

    def testDatalinkExtern(self):
        self.results = vo.spectrumsearch(self.ssa_baseurl.format(
            self.srvr.port), (30, 30), maxrec=30)

        self.assert_(len(self.results))
        datalink = next(self.results.iter_datalinks())

        row = datalink[0]
        self.assertEqual(row.semantics, "#progenitor")

        row = datalink[1]
        self.assertEqual(row.semantics, "#proc")

        row = datalink[2]
        self.assertEqual(row.semantics, "#this")

        row = datalink[3]
        self.assertEqual(row.semantics, "#preview")


__all__ = "DatalinkRunTest".split()
def suite():
    tests = []
    for t in __all__:
        tests.append(unittest.makeSuite(globals()[t]))
    return unittest.TestSuite(tests)

if __name__ == "__main__":
    try:
        module = find_current_module(1, True)
        pkgdir = os.path.dirname(module.__file__)
        t = "testserver"
        mod = imp.find_module(t, [pkgdir])
        testserve = imp.load_module(t, mod[0], mod[1], mod[2])
    except ImportError as e:
        sys.stderr.write("Can't find test server: testserver.py:" + str(e))

    srvr = testserver.TestServer(testserverport)

    try:
        srvr.start()
        unittest.main()
    finally:
        if srvr.is_alive():
            srvr.terminate()
