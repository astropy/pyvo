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

This implementation requires the following prerequisite packages:

* numpy (1.6.0 or later)
* astropy (0.2 or later)

These must be installed before install PyVO.

As an Astropy affiliate, this package uses the Astropy build
infrastructure.  

Releases of PyVO are available from `PyPI <https://pypi.python.org/pypi/pyvo>`;
thus, it and its prerequisites can be most easily installed using ``pip``:

   pip install pyvo

Alternatively, you can download and unpack a source tar-ball
(pyvo-x.x.tar.gz).  To install directly into the python installation,
type as root user inside the distributions root directory:  

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

********
EXAMPLES
********

Many instructive examples can be found in the PyVO User's Manual
(http://pyvo.readthedocs.org).  Additional examples can be found in
the scripts directory.


**********
UNIT TESTS
**********

PyVO uses the Astropy framework for unit tests which is built into the
setup script.  To run the tests, type:

    python setup.py test

This will run all unit tests that do not require a network
connection.  To run all tests, including those that access the
network, add the --remote-data (-R) option:

    python setup.py test -R

