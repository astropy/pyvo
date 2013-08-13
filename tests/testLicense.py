#!/usr/bin/env python
"""
Tests for pyvo.dal.query
"""
import os
import sys
import shutil
import re
import imp
import glob
import unittest
import pdb

license_ref_line = \
    "# Licensed under a 3-clause BSD style license - see LICENSE.rst"
license_file = "licenses/LICENSE.rst"


class LicenseTestCase(unittest.TestCase):

    def assertHasLicenseRef(self, filename):
        with open(filename) as srcf:
            lines = srcf.readlines()

        self.assertTrue(
            len(filter(lambda ln: ln.startswith(license_ref_line), lines)) > 0,
            "%s does not have license reference line" % filename)
        self.assertTrue(lines[0].startswith(license_ref_line),
                        "license reference line is not first line in %s" %
                        license_ref_line)

    def testHasLicense(self):
        self.assertTrue(os.path.exists(license_file),
                        "license/LICENSE.rst appears to be missing (what dir are you in?)")


def list_py_files(arg, dirname, names):
    return map(lambda f: (f[:-3], os.path.join(dirname,f)),
               filter(lambda n: n.endswith(".py"), names))

for dirp, dirs, files in os.walk("pyvo"):
    for fname in files:
        if not fname.endswith(".py"):
            continue
        path = os.path.join(dirp, fname)
        name = re.sub(r'/', "_", path)
        f = "lambda s: s.assertHasLicenseRef('%s')" % path
        setattr(LicenseTestCase, "test_"+name, eval(f))

__all__ = "LicenseTestCase".split()


def suite():
    tests = []
    for t in __all__:
        tests.append(unittest.makeSuite(globals()[t]))
    return unittest.TestSuite(tests)

if __name__ == "__main__":
    unittest.main()
