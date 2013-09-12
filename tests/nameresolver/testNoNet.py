#!/usr/bin/env python
"""
Test all available tests that do not require access to the network.
"""
from __future__ import print_function, division

import sys, os, unittest, imp

if len(sys.argv) > 1:
    testdir = sys.argv[1]
else:
    testdir = os.path.dirname(sys.argv[0])
testserverport = 8081

tests = []
for t in [
    "testSesameNoNet",
    ]:
    try:
        mod = imp.find_module(t, [testdir])
        mod = imp.load_module(t, mod[0], mod[1], mod[2])
        mod.testdir = testdir
        tests += mod.suite()
    except ImportError, e:
        sys.stderr.write("Unable to load {0}: {1}\n".format (t, str(e)))

testsuite = unittest.TestSuite(tests)

if __name__ == "__main__":
    ok = unittest.TextTestRunner().run(testsuite).wasSuccessful()
    sys.exit(int(not ok))
