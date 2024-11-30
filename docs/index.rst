PyVO
====

Introduction
------------

This is the documentation for PyVO, an affiliated package for the
`astropy <https://www.astropy.org>`__ package.

PyVO lets you find and retrieve astronomical data available from archives that
support standard `IVOA <http://www.ivoa.net/>`__ virtual observatory service
protocols.

* :ref:`Table Access Protocol (TAP) <pyvo_tap>`
  -- accessing source catalogs using sql-ish queries.
* :ref:`Simple Image Access (SIA) <pyvo-sia>`
  -- finding images in an archive.
* :ref:`Simple Spectral Access (SSA) <pyvo-ssa>`
  -- finding spectra in an archive.
* :ref:`Simple Cone Search (SCS) <pyvo-scs>`
  -- for positional searching a source catalog or an observation log.
* :ref:`Simple Line Access (SLAP) <pyvo-slap>`
  -- finding data about spectral lines, including their rest frequencies.

.. note::
  If you need to access data which is not available via the Virtual Observatory
  standards, try the astropy affiliated package
  `astroquery <https://astroquery.readthedocs.io/en/latest/>`__ (and, of
  course, ask the data providers to do the right thing and use the proper
  standards for their publication).

Installation
------------
PyVO is installable via pip.

.. code-block:: bash

  pip install pyvo

Source Installation
^^^^^^^^^^^^^^^^^^^
.. code-block:: bash

  git clone http://github.com/astropy/pyvo
  cd pyvo
  python setup.py install

Requirements
------------
* numpy
* astropy
* requests

.. _getting-started:

Getting started
---------------

Data Access
^^^^^^^^^^^

Most of the interesting functionality of pyVO is through the various
data access service interfaces (SCS for catalogs, SIA for images, SSAP for
spectra, TAP for tables).  All of these behave in a similar way.

First, there is a class describing a specific type of service:

.. doctest-remote-data::

    >>> import pyvo as vo
    >>> service = vo.dal.TAPService("http://dc.g-vo.org/tap")

Once you have a service object, you can run queries with parameters
specific to the service type. In this example, a database query is enough:

.. doctest-remote-data::

    >>> resultset = service.search("SELECT TOP 1 * FROM ivoa.obscore")
    >>> resultset
    <DALResultsTable length=1>
    dataproduct_type dataproduct_subtype ... source_table
                                         ...
         object             object       ...    object
    ---------------- ------------------- ... ------------
               image                     ... ppakm31.maps

What is returned by the search method is a to get a resultset object, which
essentially works like a numpy record array.  It can be processed either by
columns:

.. doctest-remote-data::

    >>> row = resultset[0]
    >>> column = resultset["dataproduct_type"]

or by rows.

.. doctest-remote-data::

    >>> for row in resultset:
    ...   calib_level = row["calib_level"]

For more details on how to use data access services see :ref:`pyvo-data-access`

Registry search
^^^^^^^^^^^^^^^

PyVO also contains a component that lets your programs interrogate the
IVOA Registry in a simple way.  For instance, to iterate over all TAP
services supporting the obscore data model (which lets people publish
observational datasets through TAP tables), you can write:

.. doctest-remote-data::

    >>> for service in vo.regsearch(datamodel="obscore"):
    ...   print(service['ivoid'])  # doctest: +IGNORE_OUTPUT
    ivo://aip.gavo.org/tap
    ivo://archive.stsci.edu/caomtap
    ivo://astro.ucl.ac.uk/tap
    ivo://astron.nl/tap
    ivo://asu.cas.cz/tap
    ...
    ivo://xcatdb/3xmmdr7/tap
    ivo://xcatdb/4xmm/tap


Using ``pyvo``
--------------

.. toctree::
   :maxdepth: 1

   dal/index
   registry/index
   discover/index
   io/index
   auth/index
   samp
   mivot/index
   utils/index
   utils/prototypes
