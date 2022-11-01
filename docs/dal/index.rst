.. _pyvo-data-access:

************************
Data Access (`pyvo.dal`)
************************

This subpackage provides access to the various data servies in the VO.

Getting started
===============

Service objects are created with the service url and provide service-specific
metadata.

.. doctest-remote-data::

    >>> import pyvo as vo
    >>> service = vo.dal.SIAService("http://dc.zah.uni-heidelberg.de/lswscans/res/positions/siap/siap.xml")
    >>> print(service.description)
    Scans of plates kept at Landessternwarte Heidelberg-Königstuhl. They
    were obtained at location, at the German-Spanish Astronomical Center
    (Calar Alto Observatory), Spain, and at La Silla, Chile. The plates
    cover a time span between 1880 and 1999.
    <BLANKLINE>
    Specifically, HDAP is essentially complete for the plates taken with
    the Bruce telescope, the Walz reflector, and Wolf's Doppelastrograph
    at both the original location in Heidelberg and its later home on
    Königstuhl.

They provide a ``search`` method with varying standard parameters for
submitting queries.

.. doctest-skip::

    >>> resultset = service.search(pos=pos, size=size)

which returns a :ref:`resultset <pyvo-resultsets>`.

Individual services may define additional, custom parameters.  You can pass
these to the ``search`` method as (case-insensitive) keyword arguments.

Call the method ``describe`` to print human-readable service metadata. You most
likely want to use this in a notebook session or similar before actually
querying the service.

See :ref:`pyvo-services` for a explanation of the different interfaces.

.. _pyvo-astro-params:

Astrometrical parameters
------------------------

Most services expose the astrometrical parameters ``pos`` and ``size`` for which
PyVO accept `~astropy.coordinates.SkyCoord` or `~astropy.units.Quantity`
objects as well as any other sequence containing right ascension and declination
in degrees, which are converted to the standard coordinate frame
(in the VO, that usually is ICRS) in the standard units (always degrees
in the VO) before they are submitted to the service.

Also, `~astropy.coordinates.SkyCoord` can be used to lookup names of
astronomical objects you are searching for.

.. doctest-remote-data::

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
    >>> time = Time(('2015-01-01T00:00:00', '2018-01-01T00:00:00'),
    ...             format='isot', scale='utc')

See :ref:`astropy-time` for explanation.

.. _pyvo-verbosity:

Verbosity
---------

Several VO protocols have the notion of “verbosity”, where 1 means “minimal
set of columns”, 2 means “columns most users can work with” and 3 ”everything
including exotic items”.  Query functions accept these values in the
``verbosity`` parameter. The exact semantics are service-specific.

Availability and capabilities
-----------------------------

VO services should offer some standard ”support” interfaces specified in
VOSI.  In pyVO, the information obtained from these endpoints can be
obtained from some service attributes.

For availability (i.e., is the service up and running?),
this is :py:attr:`~pyvo.dal.mixin.AvailabilityMixin.available`
and :py:attr:`~pyvo.dal.mixin.AvailabilityMixin.up_since`

Capabilities describe specific pieces of functionality (such as “this is a
spectral search”) and further metadata (such as ”this service will never
return more than 10000 rows”).

This information is contained in the datastructure
:py:class:`~pyvo.io.vosi.endpoint.CapabilitiesFile` available through
:py:attr:`~pyvo.dal.mixin.CapabilityMixin.capabilities`.

Exceptions
----------
See :py:mod:`pyvo.dal.exceptions`.

.. _pyvo-services:

Services
========

There are five types of services with different purposes but a similiar
interface available.

.. _pyvo_tap:

Table Access Protocol
---------------------

Unlike the other services, this one works with tables queryable by an sql-ish
language called *ADQL* instead of predefined search constraints.

.. doctest-remote-data::

    >>> tap_service = vo.dal.TAPService("http://dc.g-vo.org/tap")
    >>> tap_results = tap_service.search("SELECT TOP 10 * FROM ivoa.obscore")

As a sanity precaution, most services have some default limit of how many
rows they will return before overflowing:

.. doctest-remote-data::

    >>> print(tap_service.maxrec)
    20000

To retrieve more rows than that (often conservative) default limit, you
must override maxrec in the call to ``search``. A warning can be expected if
you reach the ``maxrec`` limit:

.. doctest-remote-data::

    >>> tap_results = tap_service.search("SELECT * FROM ivoa.obscore", maxrec=100000)  # doctest: +SHOW_WARNINGS
    DALOverflowWarning: Partial result set. Potential causes MAXREC, async storage space, etc.

Services will not let you raise maxrec beyond the hard match limit:

.. doctest-remote-data::

    >>> print(tap_service.hardlimit)
    16000000

A list of the tables and the columns within them is available in the
TAPService's :py:attr:`~pyvo.dal.TAPService.tables` attribute by using it as an
iterator or calling it's ``describe()`` method for a human-readable summary.


Uploads
^^^^^^^

Some TAP services allow you to upload your own tables to make them accessible
in queries.

For this the various query methods have a ``uploads`` keyword, which accepts a
dictionary of table name and content.

The mechanism behind this parameter is smart enough to distinct between various
types of content, either a :py:class:`~str` pointing to a local file or a
file-like object, a :py:class:`~astropy.table.Table` or
:py:class:`~pyvo.dal.query.DALResults` for an inline upload,
or a url :py:class:`~str` pointing to a remote resource.

The uploaded tables will be available as ``TAP_UPLOAD.name``.

.. note::
  The supported upload methods are available under
  :py:meth:`~pyvo.dal.tap.TAPService.upload_methods`.

.. _table manipulation:

Table Manipulation
^^^^^^^^^^^^^^^^^^

.. note::
    This is a prototype implementation and the interface might not be stable.
    More details about the feature at: :ref:`cadc-tb-upload`

Some services allow users to create, modify and delete tables. Typically, these
functionality is only available to authenticated (and authorized) users.

.. Requires proper credentials and authorization
.. doctest-skip::

    >>> auth_session = vo.auth.AuthSession()
    >>> # authenticate. For ex: auth_session.credentials.set_client_certificate('<cert_file>')
    >>> tap_service = vo.dal.TAPService("https://ws-cadc.canfar.net/youcat", auth_session)
    >>>
    >>> table_definition = '''
    ... <vosi:table xmlns:vosi="http://www.ivoa.net/xml/VOSITables/v1.0" xmlns:vod="http://www.ivoa.net/xml/VODataService/v1.1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" type="output">
    ...     <name>my_table</name>
    ...     <description>This is my very own table</description>
    ...     <column>
    ...         <name>article</name>
    ...         <description>some article</description>
    ...         <dataType xsi:type="vod:VOTableType" arraysize="30*">char</dataType>
    ...     </column>
    ...     <column>
    ...         <name>count</name>
    ...         <description>how many</description>
    ...         <dataType xsi:type="vod:VOTableType">long</dataType>
    ...     </column>
    ... </vosi:table> '''
    >>> tap_service.create_table(name='test_schema.test_table', definition=StringIO(table_definition))

Table content can be loaded from a file or from memory. Supported data formats:
tab-separated values (tsv), comma-separated values (cvs) or VOTable (VOTable):

.. doctest-skip::

    >>> tap_service.load_table(name='test_schema.test_table',
    ...                        source=StringIO('article,count\narticle1,10\narticle2,20\n'), format='csv')

Users can also create indexes on single columns:
.. doctest-skip::

    >>> tap_service.create_index(table_name='test_schema.test_table', column_name='article', unique=True)

Finally, tables and their content can be removed:

.. doctest-skip::

    >>> tap_service.remove_table(name='test_schema.test_table')


.. _pyvo-sia:

Simple Image Access
-------------------
Like the name says, this service serves astronomical images.

Basic queries are done with the ``pos`` and ``size`` parameters described in
:ref:`pyvo-astro-params`, with ``size`` being the rectangular region around
``pos``.

.. doctest-remote-data::

    >>> pos = SkyCoord.from_name('Eta Carina')
    >>> size = Quantity(0.5, unit="deg")
    >>> sia_service = vo.dal.SIAService("http://dc.zah.uni-heidelberg.de/hppunion/q/im/siap.xml")
    >>> sia_results = sia_service.search(pos=pos, size=size)

The dataset format, 'all' by default, can be specified:

.. doctest-remote-data::

    >>> sia_results = sia_service.search(pos=pos, size=size, format='graphics')

This would return all graphical image formats (png, jpeg, gif) available. Other
possible values are image/* mimetypes, or ``metadata``, which returns no image
at all but instead a declaration of the additional parameters supported
by the given service.

The ``intersect`` argument (defaulting to ``OVERLAPS``) lets a program
specify the desired relationship between the region of interest and the
coverage of the images (case-insensitively):

.. doctest-remote-data::

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
Access to (one-dimensional) spectra resembles image access, with some
subtile differences:

The size parameter is called ``diameter`` here, and hence the search
region is always circular with ``pos`` as center:

.. doctest-remote-data::

    >>> ssa_service = vo.dal.SSAService("http://www.isdc.unige.ch/vo-services/lc")
    >>> ssa_results = ssa_service.search(pos=pos, diameter=size)

SSA queries can be further constrained by the ``band`` and ``time`` parameters.

.. doctest-remote-data::

    >>> ssa_results = ssa_service.search(
    ...     pos=pos, diameter=size,
    ...     time=time, band=Quantity((1e-13, 1e-12), unit="meter")
    ... )


Simple Cone Search
------------------
The Simple Cone Search returns results – typically catalog entries –
within a circular region on the sky defined by the parameters ``pos``
(again, ICRS) and ``radius``:

.. doctest-remote-data::

    >>> scs_srv = vo.dal.SCSService('http://dc.zah.uni-heidelberg.de/arihip/q/cone/scs.xml')
    >>> scs_results = scs_srv.search(pos=pos, radius=size)

This service exposes the :ref:`verbosity <pyvo-verbosity>` parameter

Simple Line Access
------------------
This service let you query for spectral lines in a certain ``wavelength``
range. The unit of the values is meters, but any unit may be specified using
`~astropy.units.Quantity`.

Jobs
====
Some services, most notably TAP ones, allow asynchronous operation
(i.e., you submit a job, receive a URL where to check for updates, and
then can go away) using a VO standard called UWS.

These have a ``submit_job`` method, which has the same
parameters as their ``search`` but start a server-side job instead of waiting
for the result to return.

This is particulary useful for longer-running queries or when you want
to run several queries in parallel from one script.

.. note::
    It is good practice to test the query with a maxrec constraint first.

When you invoke ``submit job`` you will get a job object.

.. doctest-remote-data::

    >>> async_srv = vo.dal.TAPService("http://dc.g-vo.org/tap")
    >>> job = async_srv.submit_job("SELECT * FROM ivoa.obscore")

.. note::
    Currently, only `pyvo.dal.tap.TAPService` supports server-side jobs.

This job is not yet running yet. To start it invoke ``run``

.. doctest-remote-data::

    >>> job.run()  # doctest: +IGNORE_OUTPUT

Get the current job phase:

.. doctest-remote-data::

    >>> print(job.phase)
    EXECUTING

Maximum run time in seconds is available and can be changed with
:py:attr:`~pyvo.dal.tap.AsyncTAPJob.execution_duration`

.. doctest-remote-data::

    >>> print(job.execution_duration)
    7200.0
    >>> job.execution_duration = 3600

Obtaining the job url, which is needed to reconstruct the job at a later point:

.. doctest-remote-data::

    >>> job_url = job.url
    >>> job = vo.dal.tap.AsyncTAPJob(job_url)

Besides ``run`` there are also several other job control methods:

* :py:meth:`~pyvo.dal.tap.AsyncTAPJob.abort`
* :py:meth:`~pyvo.dal.tap.AsyncTAPJob.delete`
* :py:meth:`~pyvo.dal.tap.AsyncTAPJob.wait`

.. note::
    Usually the service deletes the job after a certain time, but it is a good
    practice to delete it manually when done.

    The destruction time can be obtained and changed with
    :py:attr:`~pyvo.dal.tap.AsyncTAPJob.destruction`

Also, :py:class:`pyvo.dal.tap.AsyncTAPJob` works as a context manager which
takes care of this automatically:

.. doctest-remote-data::

    >>> with async_srv.submit_job("SELECT * FROM ivoa.obscore") as job1:
    ...     job1.run()  # doctest: +IGNORE_OUTPUT
    >>> print('job1 deleted!')
    job1 deleted!

Check for errors in the job execution:

.. doctest-remote-data::

    >>> job.raise_if_error()

If the execution was successful, the resultset can be obtained using
:py:meth:`~pyvo.dal.tap.AsyncTAPJob.fetch_result`

The result url is available under :py:attr:`~pyvo.dal.tap.AsyncTAPJob.result_uri`

.. _pyvo-resultsets:

Resultsets and Records
======================
Resultsets contain primarily tabular data and might also provide binary
datasets and/or access to additional data services.

To obtain the names of the columns in a service response, write:

.. doctest-remote-data::

    >>> tap_service = vo.dal.TAPService("http://dc.g-vo.org/tap")
    >>> resultset = tap_service.search("SELECT TOP 10 * FROM ivoa.obscore")
    >>> print(resultset.fieldnames)
    ('dataproduct_type', 'dataproduct_subtype', 'calib_level',
    'obs_collection', 'obs_id', 'obs_title', 'obs_publisher_did',
    'obs_creator_did', 'access_url', 'access_format', 'access_estsize',
    'target_name', 'target_class', 's_ra', 's_dec', 's_fov', 's_region',
    's_resolution', 't_min', 't_max', 't_exptime', 't_resolution', 'em_min',
    'em_max', 'em_res_power', 'o_ucd', 'pol_states', 'facility_name',
    'instrument_name', 's_xel1', 's_xel2', 't_xel', 'em_xel', 'pol_xel',
    's_pixel_scale', 'em_ucd', 'preview', 'source_table')


Rich metadata equivalent to what is found in VOTables (including unit,
ucd, utype, and xtype) is available through resultset's
:py:meth:`~pyvo.dal.query.DALResults.getdesc` method:

.. doctest-remote-data::

    >>> print(resultset.getdesc('s_fov').ucd)
    phys.angSize;instr.fov

.. note::
    Two convenience functions let you retrieve columns of a specific
    physics (by UCD) or with a particular legacy data model annotation
    (by utype), like this:

.. doctest-remote-data::

    >>> fieldname = resultset.fieldname_with_ucd('phys.angSize;instr.fov')
    >>> fieldname = resultset.fieldname_with_utype('obscore:access.reference')

Iterating over a resultset gives the rows in the result:

.. doctest-remote-data::

    >>> for row in resultset:
    ...     print(row['s_fov'])
    0.05027778
    0.05027778
    0.05027778
    0.05027778
    0.05027778
    0.05027778
    0.06527778
    0.06527778
    0.06527778
    0.06527778

The total number of rows in the answer is available as its ``len()``:

.. doctest-remote-data::

    >>> print(len(resultset))
    10

If the row contains datasets, they are exposed by several retrieval methods:

.. remove skip once https://github.com/astropy/pyvo/issues/361 is fixed
.. doctest-skip::

    >>> url = row.getdataurl()
    >>> fileobj = row.getdataset()
    >>> obj = row.getdataobj()

Returning the access url, the file-like object or the appropiate python object
to further work on.

As with general numpy arrays, accessing individual columns via names gives an
array of all of their values:

.. doctest-remote-data::

    >>> column = resultset['obs_id']

whereas integers retrieve rows:

.. doctest-remote-data::

    >>> row = resultset[0]

and both combined gives a single value:

.. doctest-remote-data::

    >>> value = resultset['obs_id', 0]

Row objects may expose certain key columns as properties. See the corresponding
API spec listed below for details.

* :py:class:`pyvo.dal.sia.SIARecord`
* :py:class:`pyvo.dal.ssa.SSARecord`
* :py:class:`pyvo.dal.scs.SCSRecord`
* :py:class:`pyvo.dal.sla.SLARecord`

Convenience methods are available to transform the results into
:py:class:`astropy.table.Table` or :py:class:`astropy.table.QTable` (values
as quantities):

.. doctest-remote-data::

    >>>> astropy_table = resultset.to_table()
    >>>> astropy_qtable = resultset.to_qtable()

Multiple datasets
-----------------
PyVO supports multiple datasets exposed on record level through the datalink.
To get an iterator yielding specific datasets, call
:py:meth:`pyvo.dal.adhoc.DatalinkResults.bysemantics` with the identifier
identifying the dataset you want it to return.

.. remove skip once https://github.com/astropy/pyvo/issues/361 is fixed
.. doctest-skip::

    >>> preview = next(row.getdatalink().bysemantics('#preview')).getdataset()

.. note::
  Since the creation of datalink objects requires a network roundtrip, it is
  recommended to call ``getdatalink`` only once.

Of course one can also build a datalink object from it's url.

.. TODO: define DatalinkResults
.. doctest-skip::

    >>> datalink = DatalinkResults.from_result_url(url)

Server-side processing
----------------------
Some services support the server-side processing of record datasets.
This includes spatial cutouts for 2d-images, reducing of spectra to a certain
waveband range, and many more depending on the service.

Datalink
^^^^^^^^
Generic access to processing services is provided through the datalink
interface.

.. remove skip once https://github.com/astropy/pyvo/issues/361 is fixed
.. doctest-skip::

    >>> datalink_proc = next(row.getdatalink().bysemantics('#proc'))

.. note::
  most times there is only one processing service per result, and thats all you
  need.


The returned object lets you access the available input parameters which you
can pass as keywords to the ``process`` method.

.. remove skip once https://github.com/astropy/pyvo/issues/361 is fixed
.. doctest-skip::

  >>> datalink_proc = row.getdatalink().get_first_proc()
  >>> print(datalink_proc.input_params)


For more details about this have a look at
:py:class:`astropy.io.votable.tree.Param`.

Calling the method will return a file-like object on sucess.

.. remove skip once https://github.com/astropy/pyvo/issues/361 is fixed
.. doctest-skip::

    >>> print(datalink_proc)
    >>> fobj = datalink.process(circle=(1, 1, 1))


SODA
^^^^
SODA is a service with predefined parameters, available on row-level through
:py:meth:`pyvo.dal.adhoc.SodaRecordMixin.processed` which exposes a set of
parameters who are dependend on the type of service.

- ``circle`` -- a sequence (degrees) or :py:class:`astropy.units.Quantity` of
  longitude, latitude and radius
- ``range`` -- a sequence (degrees) or :py:class:`astropy.units.Quantity` of
  two longitude values and two latitude values describing a rectangle.
- ``polygon`` -- multiple pairs of longitude and latitude points
- ``band`` -- a sequence of two values (meters) or
  :py:class:`astropy.units.Quantity` with two bandwitdh values. The right sort
  order will be ensured if converting from frequency to wavelength.


Interoperabillity over SAMP
---------------------------
Tables and datasets can be send to other astronomical applications, providing
they have support for SAMP (Simple Application Messaging Protocol).

You can either broadcast whole tables by calling ``broadcast_samp`` on the
resultset or a single product (image, spectrum) by calling this method on the
SIA or SSA record.

.. note::
  Don't forget to start the application and make sure there is a runnung SAMP
  Hub.

Underlying data structures
--------------------------
PyVO also allows access to underlying data structures.

The astropy data classes :py:class:`astropy.table.Table` and
:py:class:`astropy.table.QTable` are accessible with the
method :py:meth:`pyvo.dal.DALResults.to_table` and
:py:meth:`pyvo.dal.DALResults.to_qtable`, following astropy naming
conventions.

If you want to work with the XML data structures
:py:class:`astropy.io.votable.tree.VOTableFile` or
:py:class:`astropy.io.votable.tree.Table`, they are accessible by the
attributes :py:attr:`pyvo.dal.DALResults.resultstable` and
:py:attr:`pyvo.dal.DALResults.votable`, respectively.

Reference/API
=============

.. automodapi:: pyvo.dal
.. automodapi:: pyvo.dal.adhoc
