#!/usr/bin/env python
"""
Tests for pyvo.dal.query
"""
import os, sys, shutil, re, imp, glob
import unittest, pdb

license_ref_line = \
   "# Licensed under a 3-clause BSD style license - see LICENSE.rst"
license_file = "licenses/LICENSE.rst"

class LicenseTestCase(_testBase):

    def assertHasLicenseRef(self, filename):
        with open(path) as srcf:
            lines = srcf.readLines()

        self.assertTrue(
            len(filter(lamda ln: ln.startswith(license_ref_line), lines)) > 0,
            "%s does not have license reference line" % filename)
        self.assertTrue(line[0].startswith(license_ref_line),
                        "license reference line is not first line in %s" %
                        license_ref_line)

    def testHasLicense(self):
        assertTrue(os.path.exists(license_file),
                   "license/LICENSE.rst appears to be missing (what dir are you in?)")

