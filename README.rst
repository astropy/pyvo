PyVO
===================================

.. image:: http://img.shields.io/badge/powered%20by-AstroPy-orange.svg?style=flat
    :target: https://www.astropy.org
    :alt: Powered by Astropy Badge

.. image:: https://github.com/astropy/pyvo/workflows/CI/badge.svg?branch=main
    :target: https://github.com/astropy/pyvo/workflows/CI/badge.svg?branch=main
    :alt: CI Status

.. image:: https://codecov.io/gh/astropy/pyvo/branch/main/graph/badge.svg?token=Mynyo9xoPZ
    :target: https://codecov.io/gh/astropy/pyvo
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

Installation and Requirements
-----------------------------

Releases of PyVO are available from `PyPI <https://pypi.python.org/pypi/pyvo>`_
thus, it and its prerequisites can be most easily installed using ``pip``:

   pip install pyvo


Releases are also conda packaged and available on the ``conda-forge``
channel.


PyVO requires Python 3.8 or later.

The following packages are required for PyVO:

 * `astropy <https://astropy.org>`__ (>=4.1)
 * `requests <http://docs.python-requests.org/en/latest/>`_

The following packages are optional dependencies and are required for the
full functionality:

 * pillow

For running the tests, and building the documentation, the following
infrastructure packages are required:

* `pytest-astropy <https://github.com/astropy/pytest-astropy>`__
* requests-mock
* `sphinx-astropy <https://github.com/astropy/sphinx-astropy>`__


To install from source use ``pip``:

   pip install .[all]


Using the developer version of PyVO in testing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We recommend and encourage testing against the development version of PyVO in CI,
both for dependent libraries and notebook providers. As PyVO is a pure Python library, this can be
done as easily as pip installing the developer version from GitHub:

   pip install git+https://github.com/astropy/pyvo.git#egg=pyvo

An example for setting up development version testing for a library as a GitHub Actions Workflow can
be found in `astroquery <https://github.com/astropy/astroquery/blob/main/.github/workflows/ci_devtests.yml>`__.

Examples
--------

Many instructive examples can be found in the `PyVO Documentation <http://pyvo.readthedocs.org>`_.
Additional examples can be found in the examples directory.

Unit Tests
----------

PyVO uses the Astropy framework for unit tests which is built into the
setup script.  To run the tests, type:

    pip install .[test]
    pytest

This will run all unit tests that do not require a network
connection.  To run all tests, including those that access the
network, add the --remote-data option:

    pytest --remote-data
