.. _pyvo-data-access:

************************
Data Access (`pyvo.dal`)
************************

This subpackage provides access to the various data services in the VO.

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

Astrometric parameters
----------------------

Most services expose the astrometric parameters ``pos`` and ``size`` for which
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
astrometric parameter, such as waveband ranges.

Some services also accept `~astropy.time.Time` as ``time`` parameter.

.. doctest::

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

Capabilities
------------

VO services should offer some standard ”support” interfaces specified in
VOSI.  In pyVO, the information obtained from these endpoints can be
obtained from some service attributes.

Capabilities describe specific pieces of functionality (such as “this is a
spectral search”) and further metadata (such as ”this service will never
return more than 10000 rows”).

This information is contained in the data structure
:py:class:`~pyvo.io.vosi.endpoint.CapabilitiesFile` available through
the ``pyvo.dal.vosi.CapabilityMixin.capabilities`` attribute.

Exceptions
----------
See the ``pyvo.dal.exceptions`` module.

.. _pyvo-services:

Services
========

There are five types of services with different purposes but a mostly
similar interface available.

.. _pyvo_tap:

Table Access Protocol
---------------------

.. pull-quote::

    This protocol defines a service protocol for accessing
    general table data, including astronomical catalogs as well as general
    database tables. Access is provided for both database and table metadata
    as well as for actual table data. This protocol supports the query language
    `Astronomical Data Query Language (ADQL) <https://www.ivoa.net/documents/ADQL/>`_
    within an integrated interface.
    It also includes support for both synchronous and asynchronous queries.
    Special support is provided for spatially indexed queries using the
    spatial extensions in ADQL. A multi-position query capability permits
    queries against an arbitrarily large list of astronomical targets,
    providing a simple spatial cross-matching capability.
    More sophisticated distributed cross-matching capabilities are possible by
    orchestrating a distributed query across multiple TAP services.

    -- `Table Access Protocol <https://www.ivoa.net/documents/TAP/>`_


Consider the following example for using TAP and ADQL, retrieving 5
objects from the GAIA DR3 database, showing their id, position and
mean G-band magnitude between 19 - 20:

.. doctest-remote-data::

    >>> import pyvo as vo
    >>> tap_service = vo.dal.TAPService("http://dc.g-vo.org/tap")
    >>> ex_query = """
    ...     SELECT TOP 5
    ...     source_id, ra, dec, phot_g_mean_mag
    ...     FROM gaia.dr3lite
    ...     WHERE phot_g_mean_mag BETWEEN 19 AND 20
    ...     ORDER BY phot_g_mean_mag
    ...     """
    >>> result = tap_service.search(ex_query)
    >>> print(result)
    <DALResultsTable length=5>
        source_id              ra                dec         phot_g_mean_mag
                            deg                deg               mag
        int64             float64            float64           float32
    ------------------- ------------------ ------------------ ---------------
    2162809607452221440 315.96596187101636 45.945474015208106            19.0
    2000273643933171456  337.1829026565382   50.7218533537033            19.0
    2171530448339798784  323.9151025188806  51.27690705826792            19.0
    2171810342771336704 323.25913736080776  51.94305655940998            19.0
    2180349528028140800  310.5233961869657   50.3486391034819            19.0

While DALResultsTable has some convenience functions, is is often
convenient to directly obtain a proper astropy Table using the
``to_table`` method:

.. doctest-remote-data::

    >>> result.to_table().columns[:3]
    <TableColumns names=('source_id','ra','dec')>


To explore more query examples, you can try either the ``description``
attribute for some services. For other services like this one, try
the ``examples`` attribute.

.. doctest-remote-data::

    >>> print(tap_service.examples[1]['QUERY'])
    SELECT TOP 50 l.id, l.pmra as lpmra, l.pmde as lpmde,
    g.source_id, g.pmra as gpmra, g.pmdec as gpmde
    FROM
    lspm.main as l
    JOIN gaia.dr3lite AS g
    ON (DISTANCE(g.ra, g.dec, l.raj2000, l.dej2000)<0.01) -- rough pre-selection
    WHERE
    DISTANCE(
        ivo_epoch_prop_pos(
        g.ra, g.dec, g.parallax,
        g.pmra, g.pmdec, g.radial_velocity,
        2016, 2000),
        POINT(l.raj2000, l.dej2000)
    )<0.0002                            -- fine selection with PMs

TAPServices let you do extensive metadata inspection.  For instance,
to see the tables available on the Simbad TAP service, say:

.. doctest-remote-data::

    >>> simbad = vo.dal.TAPService("http://simbad.cds.unistra.fr/simbad/sim-tap")
    >>> print([tab_name for tab_name in simbad.tables.keys()])  # doctest: +IGNORE_WARNINGS
    ['TAP_SCHEMA.schemas', 'TAP_SCHEMA.tables', ... 'otypedef', 'otypes', 'ref']


If you know a TAP service's access URL, you can directly pass it to
:py:class:`~pyvo.dal.TAPService` to obtain a service object.
Sometimes, such URLs are published in papers or passed around through
other channels. Most commonly, you will discover them in the VO
registry (cf. :ref:`pyvo.registry<pyvo-registry>`).

To perform a query using ADQL, the ``search()`` method is used.
TAPService instances have several methods to inspect the metadata
of the service - in particular, what tables with what columns are
available - discussed below.

To get an idea of how to write queries in ADQL, have a look at
`GAVO's ADQL course`_; it is basically a standardised subset of SQL
with some extensions to make it work better for astronomy.

.. _GAVO's ADQL course: https://docs.g-vo.org/adql

Synchronous vs. asynchronous query
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In synchronous (“sync”) mode, the client keeps a connection for the
entire runtime of the query, and query processing generally starts
when the request is submitted.  This is convenient but becomes
brittle as queries have runtimes of the order of minutes, when you
may encounter query timeouts.  Also, many data providers impose
rather strict limits on the runtime allotted to sync queries.

In asynchronous (“async”) mode, on the other hand, the client just
submits a query and receives a URL that let us inspect the
execution status (and retrieve its result) later.  This means that
no connection needs to be held, which makes this mode a lot more
robust of long-running queries.  It also supports queuing queries,
which allows service operators to be a lot more generous with
resource limits.

To specify the query mode, you can use either ``run_sync()`` for
synchronous query or ``run_async()`` for asynchronous query.

.. doctest-remote-data::

    >>> job = tap_service.submit_job(ex_query)

To learn more details from the asynchronous query, let's look at the
``submit_job()`` method. This submits an asynchronous query without
starting it, it creates a new object :py:class:`~pyvo.dal.AsyncTAPJob`.

.. doctest-remote-data::

    >>> job.url
    'http://dc.g-vo.org/__system__/tap/run/async/...'

The job URL mentioned before is available in the ``url`` attribute.
Clicking on the URL leads you to the query itself, where you can check
the status(phase) of the query and decide to run, modify or delete
the job. You can also do it via various attributes:

.. doctest-remote-data::

    >>> job.phase
    'PENDING'

A newly created job is in the PENDING state.
While it is pending, it can be configured, for instance, overriding
the server's default time limit (after which the query will be
canceled):

.. doctest-remote-data::

    >>> job.executionduration = 700
    >>> job.executionduration
    700

When you are ready, you can start the job:

.. doctest-remote-data::

    >>> job.run()
    <pyvo.dal.tap.AsyncTAPJob object at 0x...>

This will put the job into the QUEUED state.  Depending on how busy
the server is, it will immediately go to the EXECUTING status:

.. doctest-remote-data::

    >>> job.phase  # doctest: +IGNORE_OUTPUT
    'EXECUTING'

The job will eventually end up in one of the phases:

* COMPLETED - if all went to plan,
* ERROR -   if the query failed for some reason;
            look at the error
            attribute of the job to find out details,
* ABORTED - if you manually killed the query using the ``abort()``
            method or the server killed your query, presumably because it hit
            the time limit.

After the job ends up in COMPLETED, you can retrieve the result:

.. doctest-remote-data::

    >>> job.phase  # doctest: +IGNORE_OUTPUT
    'COMPLETED'
    >>> job.fetch_result()  # doctest: +SKIP
    (result table as shown before)

Eventually, it is friendly to clean up the job rather than relying
on the server to clean it up once ``job.destruction`` (a datetime
that you can change if you need to) is reached.

.. doctest-remote-data::

    >>> job.delete()

For more attributes please read the description for the job object
:py:class:`~pyvo.dal.AsyncTAPJob`.

With ``run_async()`` you basically submit an asynchronous query and
return its result. It is like running ``submit_job()`` first and then
run the query manually.

Query limit
^^^^^^^^^^^

As a sanity precaution, most services have some default limit of how many
rows they will return before overflowing:

.. doctest-remote-data::

    >>> print(tap_service.maxrec)
    20000

To retrieve more rows than that (often conservative) default limit, you
must override maxrec in the call to ``search``. A warning can be expected if
you reach the ``maxrec`` limit:

.. doctest-remote-data::

    >>> tap_results = tap_service.search("SELECT * FROM arihip.main", maxrec=5)  # doctest: +SHOW_WARNINGS
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

For further information about the service's parameters, see :py:class:`~pyvo.dal.TAPService`.

.. _pyvo-sia:

Simple Image Access
-------------------

.. pull-quote::

    The Simple Image Access (SIA) protocol
    provides capabilities for the discovery, description, access, and retrieval
    of multi-dimensional image datasets, including 2-D images as well as datacubes
    of three or more dimensions. SIA data discovery is based on the
    `ObsCore Data Model <https://www.ivoa.net/documents/ObsCore/>`_,
    which primarily describes data products by the physical axes (spatial, spectral,
    time, and polarization). Image datasets with dimension greater than 2 are often
    referred to as datacubes, cube or image cube datasets and may be considered examples
    of hypercube or n-cube data. PyVO supports both versions of SIA.

    -- `Simple Image Access <https://www.ivoa.net/documents/SIA/>`_

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

For further information about the service's parameters, see :py:class:`~pyvo.dal.SIAService`.

.. _pyvo-ssa:

Simple Spectrum Access
----------------------

.. pull-quote::

    The Simple Spectral Access (SSA) Protocol (SSAP)
    defines a uniform interface to remotely discover and access one
    dimensional spectra.

    -- `Simple Spectral Access Protocol <https://www.ivoa.net/documents/SSA/>`_

Access to (one-dimensional) spectra resembles image access, with some
subtile differences:

The size parameter is called ``diameter`` here, and hence the search
region is always circular with ``pos`` as center:

.. doctest-remote-data::

    >>> ssa_service = vo.dal.SSAService("http://archive.stsci.edu/ssap/search2.php?id=BEFS&")
    >>> ssa_results = ssa_service.search(pos=pos, diameter=size)
    >>> ssa_results[0].getdataurl()
    'http://archive.stsci.edu/pub/vospectra/...'

SSA queries can be further constrained by the ``band`` and ``time`` parameters.

.. doctest-remote-data::

    >>> ssa_results = ssa_service.search(
    ...     pos=pos, diameter=size,
    ...     time=Time((53000, 54000), format='mjd'), band=Quantity((1e-13, 1e-12), unit="m"))

For further information about the service's parameters, see :py:class:`~pyvo.dal.SSAService`.

.. _pyvo-scs:

Simple Cone Search
------------------

.. pull-quote::

    The Simple Cone Search (SCS)
    API specification defines a simple query protocol for retrieving records from
    a catalog of astronomical sources. The query describes sky position and
    an angular distance, defining a cone on the sky. The response returns
    a list of astronomical sources from the catalog whose positions
    lie within the cone, formatted as a VOTable.

    -- `Simple Cone Search <https://www.ivoa.net/documents/latest/ConeSearch.html>`_

The Simple Cone Search returns results – typically catalog entries –
within a circular region on the sky defined by the parameters ``pos``
(again, ICRS) and ``radius``:

.. doctest-remote-data::

    >>> scs_srv = vo.dal.SCSService('http://dc.zah.uni-heidelberg.de/arihip/q/cone/scs.xml')
    >>> scs_results = scs_srv.search(pos=pos, radius=size)

This service exposes the :ref:`verbosity <pyvo-verbosity>` parameter.
For further information about the service's parameters, see :py:class:`~pyvo.dal.SCSService`.

.. _pyvo-slap:

Simple Line Access
------------------

.. pull-quote::

    The Simple Line Access Protocol (SLAP)
    is an IVOA data access protocol which defines a protocol for retrieving
    spectral lines coming from various Spectral Line Data Collections through
    a uniform interface within the VO framework.

    -- `Simple Line Access Protocol <https://www.ivoa.net/documents/SLAP/>`_

This service let you query for spectral lines in a certain ``wavelength``
range. The unit of the values is meters, but any unit may be specified using
`~astropy.units.Quantity`.
For further information about the service's parameters, see :py:class:`~pyvo.dal.SLAService`.

Jobs
====
Some services, most notably TAP ones, allow asynchronous operation
(i.e., you submit a job, receive a URL where to check for updates, and
then can go away) using a VO standard called UWS.

These have a ``submit_job`` method, which has the same
parameters as their ``search`` but start a server-side job instead of waiting
for the result to return.

This is particularly useful for longer-running queries or when you want
to run several queries in parallel from one script.

.. note::
    It is good practice to test the query with a maxrec constraint first.

When you invoke ``submit_job`` you will get a job object.

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

    >>> print(job.phase)  # doctest: +IGNORE_OUTPUT
    EXECUTING

Maximum run time in seconds is available and can be changed with
:py:attr:`~pyvo.dal.AsyncTAPJob.execution_duration`

.. doctest-remote-data::

    >>> print(job.execution_duration)
    7200.0
    >>> job.execution_duration = 3600

Obtaining the job url, which is needed to reconstruct the job at a later point:

.. doctest-remote-data::

    >>> job_url = job.url
    >>> job = vo.dal.tap.AsyncTAPJob(job_url)

Besides ``run`` there are also several other job control methods:

* :py:meth:`~pyvo.dal.AsyncTAPJob.abort`
* :py:meth:`~pyvo.dal.AsyncTAPJob.delete`
* :py:meth:`~pyvo.dal.AsyncTAPJob.wait`

.. note::
    Usually the service deletes the job after a certain time, but it is a good
    practice to delete it manually when done.

    The destruction time can be obtained and changed with
    :py:attr:`~pyvo.dal.AsyncTAPJob.destruction`

Also, :py:class:`pyvo.dal.AsyncTAPJob` works as a context manager which
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
:py:meth:`~pyvo.dal.AsyncTAPJob.fetch_result`

The result url is available under :py:attr:`~pyvo.dal.AsyncTAPJob.result_uri`

.. _pyvo-resultsets:

Resultsets and Records
======================
Resultsets contain primarily tabular data and might also provide binary
datasets and/or access to additional data services.

To obtain the names of the columns in a service response, write:

.. doctest-remote-data::

    >>> tap_service = vo.dal.TAPService("http://dc.g-vo.org/tap")
    >>> resultset = tap_service.search("SELECT * FROM ivoa.obscore"
    ... " WHERE obs_collection='CALIFA' AND"
    ... " 1=CONTAINS(s_region, CIRCLE(23, 42, 5))"
    ... " ORDER BY obs_publisher_did")
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
    0.01
    0.01
    0.01
    0.01
    0.01
    0.01
    0.01
    0.01
    0.01

The total number of rows in the answer is available as its ``len()``:

.. doctest-remote-data::

    >>> print(len(resultset))
    9

If the row contains datasets, they are exposed by several retrieval methods:

.. remove skip once https://github.com/astropy/pyvo/issues/361 is fixed
.. doctest-skip::

    >>> row.getdataurl()
    'http://dc.zah.uni-heidelberg.de/getproduct/califa/datadr3/V500/NGC0551.V500.rscube.fits'
    >>> type(row.getdataset())
    <class 'urllib3.response.HTTPResponse'>

Returning the access url or the a file-like object to further work on.

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

    >>> astropy_table = resultset.to_table()
    >>> astropy_qtable = resultset.to_qtable()

Datalink
--------

Datalink lets operators associate multiple artifacts with a dataset.
Examples include linking raw data, applicable or applied calibration
data, derived datasets such as extracted sources, extra documentation,
and much more.

Datalink can both be used on result rows of queries and from
datalink-valued URLs.  The typical use is to call ``iter_datalinks()``
on some DAL result; this will iterate over all datalinks pyVO finds in a
document and yields :py:class:`pyvo.dal.adhoc.DatalinkResults` instances
for them.  In those, you can, for instance, pick out items by semantics,
where the standard vocabulary datalink documents use is documented at
http://www.ivoa.net/rdf/datalink/core.  Here is how to find URLs for
previews:

.. doctest-remote-data::
    >>> rows = vo.dal.TAPService("http://dc.g-vo.org/tap"
    ... ).run_sync("select top 5 * from califadr3.cubes order by califaid")
    >>> for dl in rows.iter_datalinks():  # doctest: +IGNORE_WARNINGS
    ...     print(next(dl.bysemantics("#preview"))["access_url"])
    http://dc.g-vo.org/getproduct/califa/datadr3/V1200/IC5376.V1200.rscube.fits?preview=True
    http://dc.g-vo.org/getproduct/califa/datadr3/COMB/IC5376.COMB.rscube.fits?preview=True
    http://dc.g-vo.org/getproduct/califa/datadr3/V500/IC5376.V500.rscube.fits?preview=True
    http://dc.g-vo.org/getproduct/califa/datadr3/COMB/UGC00005.COMB.rscube.fits?preview=True
    http://dc.g-vo.org/getproduct/califa/datadr3/V1200/UGC00005.V1200.rscube.fits?preview=True

The call to ``next`` in this example picks the first link marked
*preview*.  For previews, this may be enough, but in general there can
be multiple links for a given semantics value for one dataset.

It is sometimes useful to go back to the original row the datalink was
generated from; use the ``original_row`` attribute for that (which may
be None if pyvo does not know what row the datalink came from):

.. doctest-remote-data::
  >>> dl.original_row["obs_title"]
  'CALIFA V1200 UGC00005'

Consider ``original_row`` read only.  We do not define what happens when
you modify it.

Rows from tables supporting datalink also have a ``getdatalink()``
method that returns a ``DatalinkResults`` instance.  In general, this is
less flexible than using ``iter_datalinks``, and it may also cause more
network traffic because each such call will cause a network request.

When one has a link to a Datalink document – for instance, from an
obscore or SIAP service, where the media type is
application/x-votable;content=datalink –, one can build a
DatalinkResults using
:py:meth:`~pyvo.dal.adhoc.DatalinkResults.from_result_url`:

.. doctest-remote-data::

    >>> from pyvo.dal.adhoc import DatalinkResults
    >>> # In this example you know the URL from somewhere
    >>> url = 'https://ws.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/caom2ops/datalink?ID=ivo%3A%2F%2Fcadc.nrc.ca%2FHSTHLA%3Fhst_12477_28_acs_wfc_f606w_01%2Fhst_12477_28_acs_wfc_f606w_01_drz'
    >>> datalink = DatalinkResults.from_result_url(url)
    >>> next(datalink.bysemantics("#this")).content_type
    'application/fits'


Server-side processing
----------------------
Some services support the server-side processing of record datasets.
This includes spatial cutouts for 2d-images, reducing of spectra to a certain
waveband range, and many more depending on the service.

Generic Datalink Processing Service
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Generic access to processing services is provided through the datalink
interface.

.. remove skip once https://github.com/astropy/pyvo/issues/361 is fixed
.. doctest-skip::

    >>> datalink_proc = next(row.getdatalink().bysemantics('#proc'))

.. note::
  Most datalink documents only have one processing service per dataset,
  which is why there is the ``get_first_proc`` shortcut mentioned below.


The returned object lets you access the available input parameters which you
can pass as keywords to the ``process`` method.

.. remove skip once https://github.com/astropy/pyvo/issues/361 is fixed
.. doctest-skip::

  >>> datalink_proc = row.getdatalink().get_first_proc()
  >>> print(datalink_proc.input_params)


For more details about this have a look at
:py:class:`astropy.io.votable.tree.Param`.

Calling the method will return a file-like object on success.

.. remove skip once https://github.com/astropy/pyvo/issues/361 is fixed
.. doctest-skip::

    >>> print(datalink_proc)
    >>> fobj = datalink.process(circle=(1, 1, 1))


SODA
^^^^
SODA is a service with predefined parameters, available on row-level through
:py:meth:`pyvo.dal.adhoc.SodaRecordMixin.processed` which exposes a set of
parameters which are dependent on the type of service.

- ``circle`` -- a sequence (degrees) or :py:class:`astropy.units.Quantity` of
  longitude, latitude and radius
- ``range`` -- a sequence (degrees) or :py:class:`astropy.units.Quantity` of
  two longitude values and two latitude values describing a rectangle.
- ``polygon`` -- multiple pairs of longitude and latitude points
- ``band`` -- a sequence of two values (meters) or
  :py:class:`astropy.units.Quantity` with two bandwidth values. The right sort
  order will be ensured if converting from frequency to wavelength.


Interoperabillity over SAMP
---------------------------
Tables and datasets can be send to other astronomical applications, providing
they have support for SAMP (Simple Application Messaging Protocol).

You can either broadcast whole tables by calling ``broadcast_samp`` on the
resultset or a single product (image, spectrum) by calling this method on the
SIA or SSA record.

.. note::
  Don't forget to start the application and make sure there is a running SAMP
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
:py:class:`astropy.io.votable.tree.TableElement`, they are accessible by the
attributes :py:attr:`pyvo.dal.DALResults.resultstable` and
:py:attr:`pyvo.dal.DALResults.votable`, respectively.

Reference/API
=============

.. automodapi:: pyvo.dal
.. automodapi:: pyvo.dal.adhoc
