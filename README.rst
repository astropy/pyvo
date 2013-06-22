====
PyVO
====

PyVO is a package providing access to remote data and services of the
Virtual observatory (VO) using Python.

Its development was launched by NSF/NASA-funded Virtual Astronomical
Observatory (VAO, www.usvao.org) project (formerly under the name
VAOpy) as part of its initiative to bring VO capabilities to desktop.
Its goal is allow astronomers and tool developers to access data and
services from remote archives and other web resources.  It takes
advantage VO standards to give access to thousands of catalogs,
data archives, information services, and analysis tools.  It also
takes advantage of the general capabilities of Astopy (and numpy), and
so a secondary goal is to provide a development platform for migrating
more VO capabilities into Astropy. 

Information about this package, including latest releases, can be
found at:

  http://dev.usvao.org/vao/wiki/Products/PyVO

Source code can be found on GitHub at:

  http://github.com/pyvirtobs/pyvo

This implementation requires the following prerequisite packagss:

* numpy (1.6.0 or later)
* astropy (0.2 - later versions have a different vo interface)

These must be installed before install PyVO.

As an Astropy affiliate, this package uses the Astropy build
infrastructure.  

To install directly into the python installation, type as root user: 

   python setup.py install

To install into a special directory called, say, $MYPYVO (which need
not require root permission), first be sure that astropy and numpy are
in your PYTHONPATH (if they are also installed in a non-standard
place).  Next, try: 

   python setup.py install --home=$MYPYVO

To just try out PyVO in this directory, you can build it in
"developer" mode via:

   python setup.py build_ext --inplace

In this mode, update your PYTHONPATH to include the directory
containing this file.  

**********
UNIT TESTS
**********

The PyVO unit tests have not yet been integrated into the py.test
framework used by Astropy.  (They currently use the standard unittest
module.)  Unit tests are contained in the tests subdirectory.  To run a
particular unit test script, type:

   python tests/path-to-script.py

For example:

   python tests/dal/testSIA.py

If the script contains the string "NeedsNet" in its name, it requirs
access to the network to work properly.  All other files do not
require the network, working off of local input files our local
services executed locally on-the-fly.  

A few files aggregate the running of tests from several individual
unit test files.  In particular:

  testNoNet.py -- runs all unit tests that do not require access to
                  the network to work.  
  testNeedsNet.py -- all tests that require the network to work in
                  order to complete.  

