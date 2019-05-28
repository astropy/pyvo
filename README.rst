PyVO
===================================

.. image:: http://img.shields.io/badge/powered%20by-AstroPy-orange.svg?style=flat
    :target: http://www.astropy.org
    :alt: Powered by Astropy Badge

.. image:: https://travis-ci.org/astropy/pyvo.svg
    :target: https://travis-ci.org/astropy/pyvo
    :alt: Travis Status

.. image:: https://coveralls.io/repos/github/pyvirtobs/pyvo/badge.svg?branch=master
    :target: https://coveralls.io/github/pyvirtobs/pyvo?branch=master
    :alt: Coverage Status

.. image:: https://zenodo.org/badge/10865450.svg
    :target: https://zenodo.org/badge/latestdoi/10865450


PyVO is a package providing access to remote data and services of the
Virtual observatory (VO) using Python.

Its development was launched by the NSF/NASA-funded Virtual Astronomical
Observatory (VAO, www.usvao.org) project (formerly under the name
VAOpy) as part of its initiative to bring VO capabilities to desktop.
Its goal is to allow astronomers and tool developers to access data and
services from remote archives and other web resources.  It takes
advantage of VO standards to give access to thousands of catalogs,
data archives, information services, and analysis tools.  It also
takes advantage of the general capabilities of Astopy (and numpy), and
so a secondary goal is to provide a development platform for migrating
more VO capabilities into Astropy.

Source code can be found `on GitHub <http://github.com/astropy/pyvo>`_

Releases of PyVO are available from `PyPI <https://pypi.python.org/pypi/pyvo>`_
thus, it and its prerequisites can be most easily installed using ``pip``:

   pip install pyvo

Alternatively, you can do a source install:
    python setup.py install

EXAMPLES
--------

Many instructive examples can be found in the `PyVO Documentation <http://pyvo.readthedocs.org>`_.
Additional examples can be found in the scripts directory.

UNIT TESTS
----------

PyVO uses the Astropy framework for unit tests which is built into the
setup script.  To run the tests, type:

    python setup.py test

This will run all unit tests that do not require a network
connection.  To run all tests, including those that access the
network, add the --remote-data (-R) option:

    python setup.py test -R
