

***************
Installing PyVO
***************

Information about this package, including latest releases, can be
found at:

  http://dev.usvao.org/vao/wiki/Products/PyVO

Source code can be found on GitHub at:

  http://github.com/pyvirtobs/pyvo

This implementation requires the following prerequisite packages:

* numpy
* astropy

If you install PyVO from a source distribution, these must be
installed first. 

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


