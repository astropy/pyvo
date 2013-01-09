#!/usr/bin/env python
"""
Test all available tests that do not require access to the network.
"""
import sys, os, unittest, imp

if len(sys.argv) > 1:
    testdir = sys.argv[1]
else:
    testdir = os.path.dirname(sys.argv[0])
testserverport = 8081

tests = []
for t in [
    "testQueryNoNet",
    "testSIA",
    "testCS",
    ]:
    try:
        mod = imp.find_module(t, [testdir])
        mod = imp.load_module(t, mod[0], mod[1], mod[2])
        mod.testdir = testdir
        tests += mod.suite()
    except ImportError, e:
        print >> sys.stderr, "Unable to load %s: %s" % (t, str(e))

testsuite = unittest.TestSuite(tests)

try:
    t = "aTestSIAServer"
    mod = imp.find_module(t, [testdir])
    testserver = imp.load_module(t, mod[0], mod[1], mod[2])
    testserver.testdir = testdir
except ImportError, e:
    print >> sys.stderr, "Can't find test server: aTestSIAServer.py:", str(e)

def suite():
    return testsuite

if __name__ == "__main__":
    ok = False
    srvr = testserver.TestServer(testserverport)
    try:
        srvr.start()
        ok = unittest.TextTestRunner().run(testsuite).wasSuccessful()
    finally:
        if srvr.isAlive():
            srvr.shutdown()
    sys.exit(int(not ok))

