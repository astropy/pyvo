PyVO
====

Introduction
------------

This is the documentation for PyVO, an affiliated package for the
`astropy <http://www.astropy.org>`__ package.

PyVO lets you find and retrieve astronomical data available from archives that
support standard `IVOA <http://www.ivoa.net/>`__ virtual observatory service
protocols.

* `Table Access Protocol (TAP) <http://www.ivoa.net/documents/TAP/>`_
  -- accessing source catalogs using sql-ish queries.
* `Simple Image Access (SIA) <http://www.ivoa.net/documents/SIA/>`_
  -- finding images in an archive.
* `Simple Spectral Access (SSA) <http://www.ivoa.net/documents/SSA/>`_
  -- finding spectra in an archive.
* `Simple Cone Search (SCS) <http://www.ivoa.net/documents/latest/ConeSearch.html>`_
  -- for positional searching a source catalog or an observation log.
* `Simple Line Access (SLAP) <http://www.ivoa.net/documents/SLAP/>`_
  -- finding data about spectral lines, including their rest frequencies.

.. note::
  If you need to access data which is not available via the Virtual Observatory
  standards, try the astropy affiliated package
  `astroquery <http://astroquery.readthedocs.io/en/latest/>`__ (and, of
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

  git clone http://github.com/pyvirtobs/pyvo
  cd pyvo
  python setup.py install

Requirements
------------
* numpy
* astropy
* requests

.. note::
  With numpy below version 1.14.0 there are some regression with float
  representations.

  See `<https://docs.scipy.org/doc/numpy/release.html>`__
  for details.

.. _getting-started:

Getting started
---------------

Data Access
^^^^^^^^^^^

Most of the interesting functionality of pyVO is through the various
data access service interfaces (SCS for catalogs, SIA for images, SSAP for
spectra, TAP for tables).  All of these behave in a similar way.

First, there is a class describing a specific type of service:

>>> import pyvo as vo
>>> service = vo.dal.TAPService("http://dc.g-vo.org/tap")

Once you have a service object, you can run queries with parameters
specific to the service type. In this example, a database query is enough:

>>> resultset = service.search("SELECT TOP 1 * FROM ivoa.obscore")
<Table masked=True length=1>
dataproduct_type dataproduct_subtype calib_level ... s_pixel_scale em_ucd
                                                 ...      arcs
     object             object          int16    ...    float64    object
---------------- ------------------- ----------- ... ------------- ------
           image                               1 ...            --

What is returned by the search method is a to get a resultset object, which
esseintially works like a numpy record array.  It can be processed either by
columns:

>>> row = resultset[0]
>>> column = resultset["dataproduct_type"]

or by rows.

>>> for row in resultset:
>>>   calib_level = row["calib_level"]

For more details on how to use data access services see :ref:`pyvo-data-access`

Registry search
^^^^^^^^^^^^^^^

PyVO also contains a component that lets your programs interrogate the
IVOA Registry in a simple way.  For instance, to iterate over all TAP
services supporting the obscore data model (which lets people publish
observational datasets through TAP tables), you can write:

>>> for service in vo.regsearch(datamodel="obscore"):
...   print(service)


Using `pyvo`
------------

.. toctree::
   :maxdepth: 1

   dal/index
   registry/index
   io/index
   auth/index
