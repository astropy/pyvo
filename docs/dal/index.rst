.. _pyvo-data-access:

************************
Data Access (`pyvo.dal`)
************************

This subpackage provides access to the various data servies in the VO.

Getting started
===============

Service objects are created with the service url and provide service-specific
metadata.

>>> service = vo.dal.SIAService("http://dc.zah.uni-heidelberg.de/lswscans/res/positions/siap/siap.xml")
>>> print(service.description)

They provide a ``search`` method with varying standard parameters for
submitting queries.

>>> resultset = service.search(pos=pos, size=size)

which returns a :ref:`resultset <pyvo-resultsets>`.

Additional to standard parameters, service-dependant search constraints are
supported by case-insensitive keyword parameters.

See :ref:`pyvo-services` for a explanation of the different interfaces.

.. _pyvo-astro-params:

Astrometrical parameters
------------------------

Most services expose the astrometrical parameters ``pos`` and ``size`` for which
PyVO accept `~astropy.coordinates.SkyCoord` or `~astropy.units.Quantity`
objects as well as any other sequence containing right ascension and declination
in degrees, which are converted to the right coordinate frame / unit before
submitted to the service.

Also, `~astropy.coordinates.SkyCoord` can be used to lookup names of
astronomical objects you are searching for.

>>> import pyvo as vo
>>> from astropy.coordinates import SkyCoord
>>> from astropy.units import Quantity
>>> 
>>> pos = SkyCoord.from_name('NGC 4993')
>>> size = Quantity(0.5, unit="deg")

See :ref:`astropy-coordinates` and :ref:`astropy-units` for details.

The `~astropy.units.Quantity` object is also suitable for any other
astrometrical parameter, such as waveband ranges.

Some services also accept `~astropy.time.Time` as ``time`` parameter.

>>> from astropy.time import Time
>>> time = Time(
>>>     ('2015-01-01T00:00:00', '2018-01-01T00:00:00'),
>>>     format='isot', scale='utc'
>>> )

See :ref:`astropy-time` for explanation.

.. _pyvo-verbosity:

Verbosity
---------
Some services allow to configure the amount of data to return by the
``verbosity`` parameter. The exact columns are defined by the service standard.

Availability and capabilities
-----------------------------

Services may have availability and capability information, depending on the version.

For availability, this is :py:attr:`~pyvo.dal.mixin.AvailabilityMixin.available`
and :py:attr:`~pyvo.dal.mixin.AvailabilityMixin.up_since`

Capabilities define which functionallity a service is exposing at the http level.
This information is contained in the datastructure
:py:class:`~pyvo.io.vosi.endpoint.CapabilitiesFile` available through
:py:attr:`~pyvo.dal.mixin.CapabilityMixin.capabilities`.

Exceptions
----------
See :py:mod:`pyvo.dal.exceptions`.

.. _pyvo-resultsets:

Resultsets and Records
----------------------
Resultset contain primarily tabular data and might also provide binary
datasets and/or access to additional data services.

To obtain the column names:

>>> print(resultset.fieldnames)

To get metadata about a given column use :py:meth:`~pyvo.dal.query.DALResults.getdesc`

.. note::
    There are semantics which allow you to get the name of fields which fulfil a
    certain purpose, namely ``ucd`` and ``utype``.

    >>> fieldname = resultset.fieldname_with_ucd('VOX:Image_AccessReference')
    >>> fieldname = resultset.fieldname_with_utype('Access.Reference')

The object is iterable

>>> for row in resultset:
>>>     print row['accref']
...

and it's length is available via the ``len()``

>>> print(len(resultset))
9

it allows access to whole columns (as numpy array) by their name

>>> column = resultset['accref']

or a specific row by rownumber

>>> row = resultset[0]

Row objects expose certain key columns as properties:

.. TODO
    Table

.. _pyvo-services:

Services
========

There are five types of services with different purposes but a similiar
interface available.

Table Access Protocol
---------------------

Unlike the other services, this one works with tables queryable by an sql-ish
language called *ADQL* instead of predefined search constraints.

>>> tap_service = vo.dal.TAPService("http://dc.g-vo.org/tap")
>>> tap_results = tap_service.search("SELECT TOP 10 * FROM ivoa.obscore")

You can limit the maximum result row count by parameter, producing more readable
SQL:

>>> tap_results = tap_service.search(
>>>     "SELECT * FROM ivoa.obscore", maxrec=10)

The default limit:

>>> print(tap_service.maxrec)

And the hard limit:

>>> print(tap_service.hardlimit)

An overview over all available tables is exposed by
:py:attr:`~pyvo.dal.TAPService.tables`

.. _pyvo-sia:

Simple Image Access
-------------------
Like the name says, this service serves astronomical images.

Basic queries are done with the ``pos`` and ``size`` parameters described in
:ref:`pyvo-astro-params`, with ``size`` being the rectangular region around
``pos``.

>>> sia_service = vo.dal.SIAService("http://cdsarc.u-strasbg.fr/saadavizier/siaservice?collection=[vizier]")
>>> sia_results = sia_service.search(pos=pos, size=size)

The dataset format, 'all' by default, can be specified:

>>> sia_results = sia_service.search(pos=pos, size=size, format='graphics')

This would return all graphical image formats (png, jpeg, gif) available. Other
possible values are image/* mimetypes, or ``metadata``, which returns no image
at all.

The way how the result images intersect with the search constraints are
variable, being the most greedy by selecting overlapping images by default.

>>> sia_results = sia_service.search(pos=pos, size=size, intersect='covers')

Available values:
    ========= ======================================================
    COVERS    select images that completely cover the search region
    ENCLOSED  select images that are complete enclosed by the region
    OVERLAPS  select any image that overlaps with the search region
    CENTER    select images whose center is within the search region
    ========= ======================================================

This service exposes the :ref:`verbosity <pyvo-verbosity>` parameter

Simple Spectrum Access
----------------------
one-dimensional images (spectra), with some subtile differences:

It's size parameter is called ``diameter`` and expects the diameter of the
circular region around ``pos``.

>>> ssa_service = vo.dal.SSAService("http://www.isdc.unige.ch/vo-services/lc")
>>> ssa_results = ssa_service.search(pos=pos, diameter=size)

Since spectras are pointed observations, there is no ``intersect`` parameter.

SSA queries can be further constrained by the ``band`` and ``time`` parameters.

>>> ssa_results = ssa_service.search(
>>>     pos=pos, diameter=size,
>>>     time=time, band=Quantity((1e-13, 1e-12), unit="meter")
>>> )

Simple Cone Search
------------------
The Simple Cone Search returns results (with and without datasets) belonging
to a circular region in the sky determined by a circular region defined by the
parameters ``pos`` and ``radius``.

>>> scs_srv = vo.dal.SCSService(
>>>     'http://dc.zah.uni-heidelberg.de/arihip/q/cone/scs.xml')
>>> scs_results = scs_srv.search(pos=pos, radius=size)

This service exposes the :ref:`verbosity <pyvo-verbosity>` parameter

Simple Line Access
------------------
This service let you query for spectral lines in a certain ``wavelength``
range. The unit of the values is meters, but any unit may be specified using
`~astropy.units.Quantity`.

Jobs
====
Some services also have a ``submit_job`` method, which has the same
parameters as their ``search`` but start a server-side job instead of waiting
for the result to return.

This is useful for longer-running queries.

.. note::
    It is good practice to test the query with a maxrec constraint first.

When you invoke ``submit job`` you will get a job object.

>>> async_srv = vo.dal.TAPService("http://dc.g-vo.org/tap")
>>> job = async_srv.submit_job("SELECT * FROM ivoa.obscore")

.. note::
    Currently, only `pyvo.dal.tap.TAPService` supports server-side jobs.

This job is not yet running yet. To start it invoke ``run``

>>> job.run()

Get the current job phase:

>>> print(job.phase)
RUN

Maximum run time in seconds is available and can be changed with
:py:attr:`~pyvo.dal.tap.AsyncTAPJob.execution_duration`

>>> print(job.execution_duration)
3600
>>> job.execution_duration = 7200

Obtaining the job url, which is needed to reconstruct the job at a later point:

>>> job_url = job.url
>>> job = vo.dal.tap.AsyncTAPJob(job_url)

Besides ``run`` there are also several other job control methods:

* :py:meth:`~pyvo.dal.tap.AsyncTAPJob.abort`
* :py:meth:`~pyvo.dal.tap.AsyncTAPJob.delete`
* :py:meth:`~pyvo.dal.tap.AsyncTAPJob.wait`

.. note::
    Usually the service deletes the job after a certain time, but it is a good
    practice to delete it manually.

    The destruction time can be obtained and changed with
    :py:attr:`~pyvo.dal.tap.AsyncTAPJob.destruction`

    Also, :py:class:`pyvo.dal.tap.AsyncTAPJob` works as a context manager which
    takes care of this automatically:

    >>> with async_srv.submit_job("SELECT * FROM ivoa.obscore") as job:
    >>>     job.run()
    >>> print('Job deleted!')

Check for errors in the job execution:

>>> job.raise_if_error()

If the execution was successful, the resultset can be obtained using
:py:meth:`~pyvo.dal.tap.AsyncTAPJob.fetch_result`

The result url is available under :py:attr:`~pyvo.dal.tap.AsyncTAPJob.result_uri`

Reference/API
=============

.. automodapi:: pyvo.dal
.. automodapi:: pyvo.dal.mixin
.. automodapi:: pyvo.dal.exceptions
