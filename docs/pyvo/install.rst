

***************
Installing PyVO
***************

Information about this package, including latest releases, can be
found at:

  http://dev.usvao.org/vao/wiki/Products/PyVO

Source code can be found on GitHub at:

  http://github.com/pyvirtobs/pyvo

This implementation requires the following prerequisite packagss:

* numpy (1.6.0 or later)
* astropy (0.2 - later versions have a different vo interface)

These must be installed before installing PyVO.

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


