
.. include:: ivoareferences.rst

.. _data-access:

********************
Data Access Services
********************

In this section, we look at the interfaces for accessing remote
archives for data using the standard VO interfaces.  

Four types of data access services are currently supported by PyVO:

* `Simple Image Access (SIA) <http://www.ivoa.net/documents/SIA/>`_ -- 
  an interface for finding images in an archive
* `Simple Spectral Access (SSA) <http://www.ivoa.net/documents/SSA/>`_
  -- a service for finding spectra in an archive
* `Simple Cone Search (SCS) <http://www.ivoa.net/documents/latest/ConeSearch.html>`_ 
  -- an inteface for searching a remote source catalog or an observation log.
  In particular, you can ask such for all sources or observations
  whose positions within some distance of a particular position of the
  sky.  
* `Simple Line Access (SLAP) <http://www.ivoa.net/documents/SLAP/>`_ 
  -- a service for finding data about spectral lines, including their
  rest frequencies. 

The sub-sections below look at the PyVO interface for each type of
service in more detail.  You will find the interfaces have a common
design and thus behave in the same way.  

.. _data-access-sia:

=====================================================
Simple Image Access and the Common Interface Features
=====================================================

In this section, we will examine the API for finding images in an
archive while as well as highlight the parts of the interface that is
common to all of the data access services.  

A Simple Image Access service is a service provided by an image
archive which complies with the IVOA standard, 
`Simple Image Access (SIA) <http://www.ivoa.net/documents/SIA/>`_.
Like all data access services, one sends a query to the service via a
simple URL which is made up of a base URL and one or more *name=value*
parameters that define the query appended to it.  PyVO takes care of
building and submitting the query, but to get started we need to have
the base URL of the service.  This base URL is often called the
*access URL*. 

How do we get the access URL?  We can discover them by querying the VO
Registry (see :ref:`registry-access`).  Also, to help you get started,
we also list a few sample services in :ref:`sample_sia_services`.  

For the examples below, we assume that you have imported PyVO via the
following:

>>> import pyvo as vo

.. _sia-func:

--------------------------
The Simple Search Function
--------------------------

As illustrated in :ref:`getting-started-examples`, you can query a
data access service through a simple function from the pyvo module.
For images, this is the :py:func:`~pyvo.imagesearch` function.  Here's
an example searching for PNG-formatted preview images from the NASA
HEASARC `SkyView <http://skyview.gsfc.nasa.gov/>`_ archive of sky
surveys. 

>>> url = 'http://skyview.gsfc.nasa.gov/cgi-bin/vo/sia.pl?'
>>> previews = vo.imagesearch(url, pos=(350.85, 58.815), size=(0.25, 0.25), format='image/png')
>>> previews.nrecs
43
>>> len(previews)
43

What is returned is a list of records in which one describes an image
that is available from the archive.  We have not downloaded any actual
files, yet; this is just information about them.  One bit of the
information is the URL we can use to download it.  

This example shows that the archive has 43 images available.  You'll
notice that we displayed this number in two ways.  It shows that our
response comes packaged in a results object that has some attributes
and, as we'll see, functions that help you understand and navigate its
contents.  It also implies that it can behave like a list.  This is
common to all results from data access searches.  

The list behavior makes it easy to iterate through the results and do
something with them, like print information about the images and
download them:

.. code-block:: python

   import os
   os.mkdir('skyview_images')

   for image in previews:
       print 'fetching', image.title
       image.cachedataset(dir='skyview_images')

We might highlight now a few things that are specific to the 
:py:func:`~pyvo.imagesearch` function.  You can see that we control the
format of the images that are selected and returned with the
``format`` argument.  To select a specific format, you give it a mime
type; for example, you can ask only for FITS images with
``format='image/fits'``.  If we just wanted graphical preview images,
but didn't care what specific format, we could say,
``format='graphic'``.  If we want to see all available formats we
could specify ``format='all'`` or leave the argument out of the call
altogether: 

>>> images = vo.imagesearch(url, pos=(350.85, 58.815), size=0.25)

Another parameter called :py:attr:`~pyvo.dal.sia.SIAQuery.intersect`
makes the service more picky about how the images returned intersect
with the search box.   For example, if you are search a fairly small
region of the sky with an interest in high resolution observations,
then you can add ``intersect='enclosed'`` to require that the image be
completely enclosed by the search region to be returned; this can be
helpful for filtering out low-resolution survey images from your
results.  

A service may support more search parameters than just the ones names
as arguments to the :py:func:`~pyvo.imagesearch` function.  Some
parameters correspond to ones defined by the `SIA standard`_ but are
used less often.  (The list of standard parameter names are listed in 
:py:attr:`SIAResults.std_parameters <pyvo.dal.sia.SIAResults.std_parameters>`.)  
The service may support its own custom parameters as well.  Arbitrary
parameters can be included in the query by passing them as named
keyword=value arguments to the function:

>>> nvssims = vo.imagesearch(url, pos=(350.85, 58.815), size=0.2, survey='nvss')

It's worth remembering that the whenever you access a service over the
network, things can go wrong:  you may loose your network connection,
the remote site might go down, the specific service may go down, and
so on.  In the VO, access to some services can fail if the service is
not sufficiently compliant with the underlying standard.  In all such
cases, PyVO will throw a useful exception; these are discussed below in
:ref:`data-access-exceptions`.  So when you encounter an error while
accessing a service, keep in mind:

* the problem may not be with your query or the PyVO software; it may
  be the remote service.
* if you are accessing many services as part of a script, be sure to
  catch exceptions to allow for graceful recovery.  


.. _sia-results:

------------------
The Results Object
------------------

When you send a query to a VO data access service, it returns a table
of matches in `VOTable <http://www.ivoa.net/documents/VOTable/>`_
format.  PyVO uses the Astropy VOTable parser (``astropy.io.votable``)
to parse the file and then raps it in a helper class that helps you
access the results.  

With the :py:func:`~pyvo.imagesearch` function, the results come in
the form of an :py:class:`~pyvo.dal.sia.SIAResults` 
class.  Most of its capabilities comes from the more general 
:py:class:`~pyvo.dal.query.DALResults` class which is common to all the
data access services.  It provides some public attributes and
functions that can be helpful for interpreting.  Four attributes of
interest are:

==============================================  =========================================================
attribute                                       description
==============================================  =========================================================
:py:attr:`~pyvo.dal.query.DALResults.nrecs`     the number of records (e.g. image descriptions) returned in the result.
            
----------------------------------------------  ---------------------------------------------------------
:py:attr:`~pyvo.dal.query.DALResults.queryurl`  the full query that was sent to the service, including 
                                                all the search parameters.
----------------------------------------------  ---------------------------------------------------------
:py:attr:`~pyvo.dal.query.DALResults.votable`   the wrapped :py:class:`astropy.io.votable.tree.Table` object 
                                                containing the results (see 
                                                :ref:`Using Astropy to Process Results`)
----------------------------------------------  ---------------------------------------------------------
:py:attr:`~pyvo.dal.query.DALResults.table`     an :py:class:`astropy.table.Table` version of the results (see 
                                                :ref:`Using Astropy to Process Results`)
==============================================  =========================================================

As we've noted, the results are fundementally a table where the rows 
reflect, in the case of SIA and the :py:func:`~pyvo.imagesearch` function, 
matching images available from the archive.  The columns of the table 
represent the image metadata.  You find out the names of these columns
with the :py:meth:`~pyvo.dal.query.DALResults.fieldnames()` method:

>>> previews.fieldnames()
[u'Survey', u'Ra', u'Dec', u'Dim', u'Size', u'Scale', u'Format', u'PixFlags',
 u'URL', u'LogicalName']

Most image services let you control the amount of metadata you get
back with the :py:attr:`~pyvo.dal.sia.SIAQuery.verbosity`
parameter. (Passing ``verbosity=3`` to :py:func:`~pyvo.imagesearch`
will return all the columns the service has available.)

You can get more information about a column either 
:py:meth:`~pyvo.dal.query.DALResults.getdesc` which returns the
description of the column with a given name or 
:py:meth:`~pyvo.dal.query.DALResults.fielddesc` which returns all of
the column descriptions in a list in the order they appeared in the
result.  

>>> deccol = previews.getdesc('Dec')
>>> deccol.datatype
u'double'
>>> deccol.ucd
u'POS_EQ_DEC_MAIN'

The column metadata that you can access includes:

============ ================================================================
attribute    description
============ ================================================================
name         the name given to the column by the archive
------------ ----------------------------------------------------------------
datatype     the type of the value (this corresponds to types of the VOTable 
             format, not Python types)
------------ ----------------------------------------------------------------
description  a short text description of the column
------------ ----------------------------------------------------------------
ucd          a special standard label for interpreting semantically what the 
             values represent (see below)
------------ ----------------------------------------------------------------
utype        a secondary standard label for interpreting semantically what the 
             values represent; this is more precise than the UCD (see below).
------------ ----------------------------------------------------------------
arraysize    a coded description of the array shape of the value (if not
             provided, defaults to a scalar)
============ ================================================================

Some of this metadata is optional; thus, an archive may not provide
all of them.  

It's worth noting that the column names are not standardized.  That is,
archives can name these columns as they see best.  PyVO uses either
the special UCD or UType attribute (whose values are set by the data
access standard) to figure out what the columns represent.  This help
comes into play when you look at individual rows of the table.  

You can extract an entire column using the 
:py:meth:`~pyvo.dal.query.DALResults.getcolumn` method:

>>> decs = previews.getcolumn('Dec')
>>> decs = previews.table['Dec']     # equivalent

The result will be a Numpy masked array.  Note that if you are accessing
data by columns, a more flexible interface is provided by the Astropy
Table instance, available via the
:py:attr:`~pyvo.dal.query.DALResults.table` attribute  (see
:ref:`Using Astropy to Process Results`).  

Often, however, when dealing with data access query results, it is
more convenient to process them by rows.  To make this easier, you can
deal with the results as if it were a list of records.  That is, you
can:

* use ``len()`` to determine number of records in the results
* you can access a record via "bracket", ``[]``, operator:

  >>> first_rec = previews[0]
  >>> last_rec = previews[-1]

* and, you can iterate through the records using a ``for`` loop:

  >>> for rec in previews:
  ...    print rec.ra, rec.dec, rec.title


Finally, we mention that the result objects support the `PEP 249`_
standard, the Python Database API (DB-APIv2) as an alternative way to
iterate through the results.  To use this interface, call the 
:py:meth:`~pyvo.dal.query.DALResults.cursor` method which will return
a DB-APIv2 ``Cursor`` instance.  See the `PEP 249`_ standard for more
details.  

.. _sia-rec:

-----------------
The Result Record
-----------------

As we saw in the previous section, you can iterate through a query
results object to get at individual records.  These records are
specialized for the particular type of service you queried, but there
is some common behavior.  For example, for all data access services,
the record behaves like an immutable dictionary where the keys are the
names of the columns from the result table:

>>> first = previews[0]
>>> first.keys()
[u'Survey', u'Ra', u'Dec', u'Dim', u'Size', u'Scale', u'Format', u'PixFlags',
 u'URL', u'LogicalName']
>>> first['Format']
'image/png'

As was mentioned in the previous subsection, the column names are not
standardized, so PyVO uses other metadata figure out what the columns
contain regardless of what they are called.  To make it easier to
access, PyVO makes certain values available as attributes of the
record.  For example, the title of the image, which SkyView calls
"LogicalName", is made available via the ``title`` attribute:

>>> first.title
2massh
>>> first.ra
350.85000000000002

The data PyVO can expect to find depends on the type of service that
was called.  Thus, for each type of service, PyVO provides a
specialized class.  In the case of results from
:py:func:`~pyvo.imagesearch`, an individual record is available as an 
:py:class:`~pyvo.dal.sia.SIARecord` instance.  Here are the standard
attributes it provides:

==========================================  =========================================================
attribute                                   description
==========================================  =========================================================
:py:attr:`~pyvo.dal.sia.SIARecord.ra`       the IRCS right ascension of the center of the image 
                                            in decimal degrees
------------------------------------------  ---------------------------------------------------------
:py:attr:`~pyvo.dal.sia.SIARecord.dec`      the IRCS declination of the center of the image
                                            in decimal degrees            
------------------------------------------  ---------------------------------------------------------
:py:attr:`~pyvo.dal.sia.SIARecord.title`    the name or identifier of the image as given by
                                            the archive
------------------------------------------  ---------------------------------------------------------
:py:attr:`~pyvo.dal.sia.SIARecord.format`   the format of the image
------------------------------------------  ---------------------------------------------------------
:py:attr:`~pyvo.dal.sia.SIARecord.dateobs`  the modified Julien date (MJD) of the mid-point of 
                                            the observational data that went into the image
                                            (optional)
------------------------------------------  ---------------------------------------------------------
:py:attr:`~pyvo.dal.sia.SIARecord.naxes`    the number of axes in the image (optional)
------------------------------------------  ---------------------------------------------------------
:py:attr:`~pyvo.dal.sia.SIARecord.instr`    the name of the instrument (or instruments) that 
                                            produced the data that went into this image.
------------------------------------------  ---------------------------------------------------------
:py:attr:`~pyvo.dal.sia.SIARecord.acref`    the URL that can be used to retrieve the image.  
==========================================  =========================================================

When the data access service search for datasets, as is the case with 
:py:func:`~pyvo.imagesearch` and :py:func:`~pyvo.spectrumsearch`, one
of the columns in the result will be a URL for downloading the
dataset.  There are two record methods that are particularly helpful
for downloading the dataset.  First, you can get the URL yourself for
downloading the dataset via the
:py:meth:`~pyvo.dal.query.Record.getdataurl`: 

>>> image = previews[0]
>>> image.getdataurl()
'http://skyview.gsfc.nasa.gov/cgi-bin/images?position=350.85%2C58.815&survey=2massh&pixels=300%2C300&sampler=Clip&size=0.25%2C0.25&projection=Tan&coordinates=J2000.0&nofits=1&quicklook=png&return=png'

The :py:meth:`~pyvo.dal.query.Record.cachedataset` will use this URL
to actually download the image:

>>> image.title
'2massh'
>>> image.format
'image/png'
>>> image.cachedataset("2massh.png")

This will simply save the downloaded image in the current directory
with the name ``2massh.png``.  

:py:meth:`~pyvo.dal.query.Record.cachedataset` can help you out with
filenames when downloading a bunch of images:

>>> import os
>>> os.mkdir("skyview_previews")
>>> for image in previews:
...     image.cachedataset(dir="skyview_previews")

In the above example, :py:meth:`~pyvo.dal.query.Record.cachedataset`
will pick a default name to use based on the image title and format.
And don't worry:  if the name already exists on disk, it won't get
overwritten.  Rather :py:meth:`~pyvo.dal.query.Record.cachedataset`
will insert a sequence number into the name instead.  

.. _data-access-exceptions:

-------------------------------------
When Things Go Wrong: Handling Errors
-------------------------------------

Whenever you access a service over the network, things can go wrong:
you may lose your network connection, the remote site might go down,
the specific service may go down, and so on.  In the VO, access to
some services can fail if the service is not sufficiently compliant
with the underlying standard.  In all such cases, PyVO will throw a
useful exception.  

In other cases, a service might be mildly non-compliant, and so you
may see numereous warnings printed to your screen.  When this happens,
you will still have a result set you can work with; however, some of
the data may not be fully available (e.g. with the proper Python
type).  

So, when you encounter issues while accessing a VO service, keep in
mind:  

* the problem may not be with your query or the PyVO software; it may
  be the remote service.
* when there are warnings, the result is often still useable.
* if you are access many services as part of a script, be sure to
  catch exceptions to allow for graceful recovery.  

There are three specific kinds of errors that can occur during a data
access search call like :py:func:`~pyvo.imagesearch` and they all have
a common base class, :py:class:`~pyvo.dal.query.DALAccessError`.
Thus, if you are not picky about what might go wrong, you can catch
just this base class.  For instance, recall our example from
:ref:`getting-started-examples` in which we were searching several
services: 

.. code-block:: python

   for arch in archives:
       print "searching %s..." % arch.shortname

       try:
            matches = arch.search(pos=pos, size=0.25)
       except vo.DALAccessError, ex:
            print "Trouble accessing %s archive (%s)"\
                  % (arch.shortname, str(ex))
            continue
       print "...found %d images" % matches.nrecs

In this example, if something went wrong, we just reported the problem
and went onto the next service.  

You can distinguish between three different errors:

============================================  ===================================================================================
Exception class                               description of failure
============================================  ===================================================================================
:py:class:`~pyvo.dal.query.DALServiceError`   an exception indicating a failure communicating with a DAL service.  This will be 
                                              thrown when the service is either unreachable or returns with an HTTP protocol 
                                              error.
--------------------------------------------  -----------------------------------------------------------------------------------
:py:class:`~pyvo.dal.query.DALFormatError`    an exception indicating that a DAL response contains fatal format errors.  This 
                                              will be thrown if the return VOTable is unparse-able due to format errors (like
                                              being illegal XML).
--------------------------------------------  -----------------------------------------------------------------------------------
:py:class:`~pyvo.dal.query.DALQueryError`     an exception indicating an error by a working DAL service while processing a query.
                                              In this case, the service returns with a legal response but is reporting a problem
                                              preventing records to be returned.  Common reasons for this include illegal input
                                              parameters or the number of results exceeds the service's limits.  
============================================  ===================================================================================

The first two indicate a problem with the service while the third one
indicates a user/client error.  The first two have a common base
exception called :py:class:`~pyvo.dal.query.DALProtocolError` which
you can catch handle service errors separatel from user errors.  




.. _sia-query:

-------------------
Using Query Objects
-------------------

Internally, the data access search functions like
:py:func:`~pyvo.imagesearch` uses a special query class to execute the
query.  This class can sometimes be useful at the query level.  Query
classes are specialized to the type of service being accessed and have
built-in knowledge the input parameters it accepts.  In the case of
searching for images via an SIA service,  one can use the 
:py:class:`~pyvo.dal.sia.SIAQuery` class.  

With a query class, you create an instance, set the query parameters,
and then execute it:

.. code-block:: python

   from pyvo.dal.sia import SIAQuery

   url = 'http://skyview.gsfc.nasa.gov/cgi-bin/vo/sia.pl?survey=dss2&'
   query = SIAQuery(url)
   query.pos = (350.85, 58.815)
   query.size = 0.25
   query.format = 'image/fits'

   images = query.execute()

Where the query object can be useful is when you want to reuse it,
altering it slightly for many different queries.  In the next example
we use it to get DSS cutouts for a list of sources:

.. code-block:: python

   source_pos = [(202.469575, 47.19525833),
                 (210.802125, 54.34808333),
                 (184.74008333, 47.30371944)]

   for pos in source_pos:
       query.pos = pos
       try:
           images = query.execute()
       except DALAccessError, ex:
           print "Trouble querying at pos=(%d,%d); skipping..." % pos
           continue

       for image in images:
           image.cachedataset()

Or you can send the same query to different services to find out what
they have in the same area of the sky:

.. code-block:: python

   services = ['http://skyview.gsfc.nasa.gov/cgi-bin/vo/sia.pl?survey=nvss&',
               'http://skyview.gsfc.nasa.gov/cgi-bin/vo/sia.pl?survey=2massh&',
               'http://skyview.gsfc.nasa.gov/cgi-bin/vo/sia.pl?survey=wise1&'  ]

   for service in services:
       query.baseurl = service
       try:
           images = query_execute()
       except DALAccessError, ex:
           print "Trouble querying service; skipping..."
           continue
       print "Found", len(images), "images"

The most commonly set query constraints are available as mutable 
properties of the class.  For :py:class:`~pyvo.dal.sia.SIAQuery`, the
following properties are available for setting constraints:

.. the length of a link in the table below makes the first column
   larger than it needs to be; it can be effectively narrowed by 
   making the second column super wide.  

+---------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                    :py:class:`~pyvo.dal.sia.SIAQuery` search constraint properties                                                                                        |
+=============================================+=============================================================================================================================================================+
| :py:attr:`~pyvo.dal.sia.SIAQuery.pos`       | the center position of the search region given as a 2-element                                                                                               |
|                                             | tuple denoting RA and declination                                                                                                                           |
+---------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| :py:attr:`~pyvo.dal.sia.SIAQuery.ra`        | the right ascension part of the region's center position                                                                                                    |
+---------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| :py:attr:`~pyvo.dal.sia.SIAQuery.dec`       | the declination part of the region's center position                                                                                                        |
+---------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| :py:attr:`~pyvo.dal.sia.SIAQuery.size`      | the width and height of the search region given as a 2-element                                                                                              |
|                                             | tuple                                                                                                                                                       |
+---------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| :py:attr:`~pyvo.dal.sia.SIAQuery.intersect` | the image-region overlap constraint                                                                                                                         |
+---------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| :py:attr:`~pyvo.dal.sia.SIAQuery.format`    | the desired format of the images to be returned                                                                                                             |
+---------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| :py:attr:`~pyvo.dal.sia.SIAQuery.verbosity` | an integer indicating the amount of metadata (i.e. columns)                                                                                                 |
|                                             | that will be returned by a query                                                                                                                            |
+---------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+

.. raw:: html

   <br>
   
As a convenience, you can either set the search position via the 
:py:attr:`SIAQuery.pos <pyvo.dal.sia.SIAQuery.pos>` property
or the  :py:attr:`SIAQuery.ra <pyvo.dal.sia.SIAQuery.ra>` and
:py:attr:`SIAQuery.dec <pyvo.dal.sia.SIAQuery.dec>` properties.  Lesser used
parameters or parameters that are custom to the service can be set and
examined using the :py:meth:`~pyvo.dal.query.DALQuery.setparam` and 
:py:meth:`~pyvo.dal.query.DALQuery.getparam` methods, respectively.

You might note two other useful methods of the query class.  First is 
:py:meth:`~pyvo.dal.query.DALQuery.getqueryurl`: this will print out the
query URL it will use when you execute it:

>>> query.getqueryurl()
'http://skyview.gsfc.nasa.gov/cgi-bin/vo/sia.pl?survey=dss2&FORMAT=image%2Ffits&POS=350.85,58.815&SIZE=0.25,0.25'

This is often useful for debugging.  For instance, you can copy this
url into your browser and view the VOTable results directly.  This
method will do a validity check on the input parameters automatically
by default, raising a :py:class:`~pyvo.dal.query.DALQueryError` if an
issue is found.  You can pass ``lax=True`` to bypass this check.

If you want to work with the service response directly, perhaps use
your own parser, you can use the
:py:meth:`~pyvo.dal.query.DALQuery.execute_stream` method to execute
it.  The result will be a file-like object that will stream the raw
XML response from the service.  Other ``execute_*`` functions are
available to provide access to other forms of the output.  

We end this examination with another example of how to create a query
object, using a Service instance: 

.. code-block:: python

   from vo.sia import SIAService
   url = 'http://skyview.gsfc.nasa.gov/cgi-bin/vo/sia.pl?survey=dss2&'
   query = SIAService(url).create_query(size=0.1, format='image/fits')
   query.ra = 350.85
   query.dec = 58.815

The :py:meth:`~pyvo.dal.sia.SIAService.create_query` method both
instantiates the query object and presets several constraints, the
same provide by the :py:func:`~pyvo.imagesearch` function.  This is
method is a feature of a *service class*, the topic of the next
subsection.  

.. _service-objects:

---------------
Service Objects
---------------

Each of the data access services have an associated Service class, a
class that represents a specific service itself.  At a minimum, it
will simply wrap a service's access URL; however, when created as a
result of a registry query, service objects can also contain other
metadata about the service (see :ref:`registry-access`).  In most
cases, you won't need to work with service objects directly.  You may
find them useful in scripts that have to manage many services in a
session.  

Here's a simple way to create a service instance:

.. code-block:: python

   url = 'http://skyview.gsfc.nasa.gov/cgi-bin/vo/sia.pl?survey=dss2&'
   service = vo.sia.SIAService(url)

You can get service instances from the results of a registry query: 

>>> hla = vo.regsearch(['Hubble Legacy Archive'], servicetype='image')
>>> hla.nrecs
1
>>> service = hla[0].to_service()
>>> service.info.description
'The Hubble Space Telecope Legacy Archive (HLA) was developed at the Space Telescope Science Institute to optimize the science return from HST instruments. This resource is an image service which accesses all HLA observation data. The calibrated data is fully online with several forms of access including footprint visualization, composite images, extracted spectra and source lists.'

You can search a service with its :py:meth:`~pyvo.dal.sia.SIAService.search`
method; its signature is just like the plain function, except the
access URL is not needed:

.. code-block:: python

   results = service.search(pos=(350.85,58.815), size=0.1)

Or, you can use its :py:meth:`~pyvo.dal.sia.SIAService.create_query`
method to create a query object:

.. code-block:: python

   query = service.create_query()  # no search parameters are set
   query = service.create_query(size=0.1, format='image/fits')

A Service Object that is embedded with metadata can be useful in some
contexts such as a GUI application where you might want an object that
represents a service to be self-describing.  

--------------------------------------
Summary of Common Data Access Features
--------------------------------------

In this section, we've examined the API for finding images using the
`Simple Image Access standard service <http://www.ivoa.net/documents/SIA/>`_,
highlighting the features that are common to all the data access
services.  For reference, we summarize those common features here:

* Data access searches can be executed via functions available in the 
  :py:mod:`pyvo` module.  These include :py:func:`~pyvo.imagesearch()`,
  :py:func:`~pyvo.spectrumsearch()`, :py:func:`~pyvo.conesearch()`,
  and :py:func:`~pyvo.linesearch()`.  (:py:func:`~pyvo.regsearch()`,
  used for discovering services, works in a similar way.)  See
  :ref:`sia-func`. 

* To connect with a data access services, you need its *access URL*, a
  base URL that PyVO uses to build and execute your query.  This is
  passed as the first argument to the data access service or it can be
  used to create a query object.  See :ref:`sia-func`. 

* The results of a search query is a results object (a subclass of the
  :py:class:`~pyvo.dal.query.DALResults` class) which wraps around the
  parsed VOTable response.  Each row in the table represents matched
  item, such as an image or a catalog record.  See :ref:`sia-results`.

* There are three ways to interact with the results:

  * You can iterate through the records, treating the results object
    like a list.  Individual record objects give you intelligent
    access to the record metadata.
  * You can treat the results as an Astropy
    :py:class:`~astropy.table.Table`; this is especially useful for
    catalog results that you might combine with your own data.
  * You can interact with the results directly as a VOTable 
    :py:class:`~astropy.io.votable.tree.Table`.  While less flexible
    than a general Astropy :py:class:`~astropy.table.Table`, it
    retains all of the VOTable-specific metadata.  

  See :ref:`sia-results`.

* When you iterate through a results instance to get at individual
  records, the records will be a specialization of the the
  :py:class:`~pyvo.dal.query.Record` class.  You can access key
  standard metadata as properties of the records.  The properties
  available depend on the type of service the results come from.  
  See :ref:`sia-results` and :ref:`sia-rec`.  

* If the service searches for datasets (i.e. :py:func:`~pyvo.imagesearch()`
  and :py:func:`~pyvo.spectrumsearch()`), you can access the dataset
  via the record instance.  You can use either 
  :py:meth:`~pyvo.dal.query.Record.getdataurl` to get the URL to the
  dataset, or you can use :py:meth:`~pyvo.dal.query.Record.cachedataset` 
  to actually download it to disk.  See :ref:`sia-rec`. 

* If a problem occurs while accessing a service, PyVO will raise a 
  specialized exception derived from 
  :py:class:`~pyvo.dal.query.DALAccessError`.  When accessing many
  services (say, in a script), it's useful to catch these exceptions
  as a guard against services that are down or don't operate
  properly.  See :ref:`data-access-exceptions`.  

* An alternative way to create data access queries is with a *query
  object*.  This can be useful when you want to reuse queries, say,
  across many sources or services.  The
  :py:meth:`~pyvo.dal.query.DALQuery.getqueryurl` method will give you
  the full query URL that will be sent to the service, which can be
  helpful for debugging.  See :ref:`sia-query`.  

* Service objects are also available for representing a service; there
  is a class for each type of service.  These are not normally used
  directly by users, but they can be helpful when managing a number of
  different services discovered from a registry.  See
  :ref:`service-objects`. 

.. _sample_sia_services:

---------------------------
A Few Sample Image Services
---------------------------

You can discover image services with queries to the VO registry (see
:ref:`registry-access`).  Here, though, list a few service access URLs
that can be used with the examples shown above.  

NASA HEASARC SkyView Archive:
    *http://skyview.gsfc.nasa.gov/cgi-bin/vo/sia.pl?*

Hubble Legacy Archive (HLA):
    *http://hla.stsci.edu/cgi-bin/hlaSIAP.cgi?imagetype=best&inst=ACS,ACSGrism,WFC3,WFPC2,NICMOS,NICGRISM,COS,STIS,FOS,GHRS&proprietary=false&*

Digitized Sky Survey (DSS2)::
    *http://skyview.gsfc.nasa.gov/cgi-bin/vo/sia.pl?survey=dss2&*

NRAO VLA Sky Survey (NVSS)::
    *http://skyview.gsfc.nasa.gov/cgi-bin/vo/sia.pl?survey=nvss&*

IRSA Two Micron All-Sky Survey (2MASS)::
    *http://skyview.gsfc.nasa.gov/cgi-bin/vo/sia.pl?survey=2mass&*

.. _data-access-ssa:

======================
Simple Spectrum Access
======================

Searching for spectra is much like searching for images, although the
search parameters are a little different.  Instead of searching a
rectangular region of the sky, we look for spectra falling within a
circular region of the sky.  Nevertheless, the spectrum search API
follows the same pattern as described in the previous section
(:ref:`data-access-sia`).

.. _ssa-func:

---------------------------
The Spectra Search Function
---------------------------

The :py:func:`~pyvo.spectrumsearch` function can be used to find
spectra from some region of the sky.  Here's an example of search for
spectra of lensed QSOs in the direction of the Coma cluster:

>>> url = 'http://dc.zah.uni-heidelberg.de/mlqso/q/q/ssap.xml?'
>>> spectra = vo.spectrumsearch(url, pos=(194.9529, 27.9805556), size=0.1)
>>> len(spectra)
180

You can restrict the results to a specific format.  This service happens to 
have previews in JPEG format:

>>> previews = vo.spectrumsearch(url, pos=(194.9529, 27.9805556), size=0.1, format='image/jpeg')
>>> len(spectra)
36

In addition to accepting formats values as MIME-type names, some
special values accepted, including "fits" for FITS format and "xml"
for VOTable format:

>>> spectra = vo.spectrumsearch(url, pos=(194.9529, 27.9805556), size=0.1, format='fits')
>>> len(spectra)
36

See the :py:attr:`pyvo.dal.ssa.SSAQuery.format` for a full enumeration of
the special format values.  

Just like searching for images, you can iterate through your results
to process the spectra:

.. code-block:: python

   import os
   os.mkdir("cdfs-spectra")

   for spec in spectra:
       print "Downloading %s..." % spec.title
       spec.cachedataset(dir="cdfs-spectra")

.. _ssa-rec:

----------------------------
Spectrum Results and Records
----------------------------

The results object returned by a spectrum search the same interface as
what is returned from a image search (see :ref:`sia-results`):

* you can treat the results like a list of records: iterate through
  the records or access specific records with the bracket
  (``[``*i*``]``) operator.  
* Use :py:meth:`~pyvo.dal.query.DALResults.fieldnames()` and 
  :py:meth:`~pyvo.dal.query.DALResults.fielddesc` to access the record
  field names and descriptions.  
* Handle the results as a Astropy :py:class:`~astropy.table.Table` or 
  or VOTable :py:class:`~astropy.io.votable.tree.Table`.  

When you process the results like a list of records, each record will
be a :py:class:`pyvo.dal.ssa.SSARecord` instance.  Just like its image
counterpart, you can treat the record like a dictionary where the keys
are the field names:

>>> rec = spectra[0]
>>> rec.keys()
('Survey', 'Ra', 'Dec', 'Dim', 'Size', 'Scale', 'Format', 'PixFlags', 'URL', 'LogicalName')

In addition, the record provides properties that allow you to pick out
key metadata about the spectrum regardless of what the column names
are.  These include:

.. the length of a link in the table below makes the first column
   larger than it needs to be; it can be effectively narrowed by 
   making the second column super wide.  

==========================================  ==================================================================================================================
property                                    description
==========================================  ==================================================================================================================
:py:attr:`~pyvo.dal.ssa.SSARecord.ra`       the IRCS right ascension of the center of the spectrum 
                                            in decimal degrees
------------------------------------------  ------------------------------------------------------------------------------------------------------------------
:py:attr:`~pyvo.dal.ssa.SSARecord.dec`      the IRCS declination of the center of the spectrum
                                            in decimal degrees            
------------------------------------------  ------------------------------------------------------------------------------------------------------------------
:py:attr:`~pyvo.dal.ssa.SSARecord.title`    the name or identifier of the spectrum as given by
                                            the archive
------------------------------------------  ------------------------------------------------------------------------------------------------------------------
:py:attr:`~pyvo.dal.ssa.SSARecord.format`   the format of the spectrum.
------------------------------------------  ------------------------------------------------------------------------------------------------------------------
:py:attr:`~pyvo.dal.ssa.SSARecord.dateobs`  the modified Julien date (MJD) of the mid-point of 
                                            the observational data that went into the image
                                            (optional)
------------------------------------------  ------------------------------------------------------------------------------------------------------------------
:py:attr:`~pyvo.dal.ssa.SSARecord.instr`    the name of the instrument (or instruments) that 
                                            produced the data that went into this image.
------------------------------------------  ------------------------------------------------------------------------------------------------------------------
:py:attr:`~pyvo.dal.sia.SIARecord.acref`    the URL that can be used to retrieve the image
                                            (equivalent to the output of 
                                            :py:meth:`~pyvo.dal.sia.SIARecord.getdataurl`)
==========================================  ==================================================================================================================

.. raw:: html

   <br>
   
Just like retrieving images, we can download individual spectrum
datasets using the :py:meth:`~pyvo.dal.sia.SIARecord.getdataurl` 
and :py:meth:`~pyvo.dal.sia.SIARecord.cachedataset`.  

--------------------------
Search and Service Classes
--------------------------

Just as in the image search case, the spectrum interface also has a
query class (see :ref:`sia-query`) and service class (see
:ref:`service-objects`). 

The query class, :py:class:`~pyvo.dal.ssa.SSAQuery`, differs from its SIA
conterpart in the search parameters it exposes as properties:

.. the length of a link in the table below makes the first column
   larger than it needs to be; it can be effectively narrowed by 
   making the second column super wide.  

+---------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                    :py:class:`~pyvo.dal.ssa.SSAQuery` search constraint properties                                                                                        |
+=============================================+=============================================================================================================================================================+
| :py:attr:`~pyvo.dal.ssa.SSAQuery.pos`       | the center position of the circular search region given as a 2-element                                                                                      |
|                                             | tuple denoting RA and declination                                                                                                                           |
+---------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| :py:attr:`~pyvo.dal.ssa.SSAQuery.ra`        | the right ascension part of the region's center position                                                                                                    |
+---------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| :py:attr:`~pyvo.dal.ssa.SSAQuery.dec`       | the declination part of the region's center position                                                                                                        |
+---------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| :py:attr:`~pyvo.dal.ssa.SSAQuery.size`      | the diameter of the circular search region                                                                                                                  |
+---------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| :py:attr:`~pyvo.dal.ssa.SSAQuery.time`      | the range of observation time to restrict spectra to                                                                                                        |
+---------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| :py:attr:`~pyvo.dal.ssa.SSAQuery.format`    | the desired format of the images to be returned                                                                                                             |
+---------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+

.. raw:: html

   <br>
   
The SSA service standard defines a large number of additional
(optional) constraints that can be set via the 
:py:meth:`~pyvo.dal.query.DALQuery.setparam` method.  The  
:py:class:`~pyvo.dal.ssa.SSAQuery` documentation describes them all
(see the :py:attr:`~pyvo.dal.query.DALQuery.std_parameters`
attribute).  

Note that there is also a Service class, 
:py:class:`~pyvo.dal.ssa.SSAService`, for SSA services which act just
like its SIA counterpart.  

.. _data-access-scs:

===================================================
Searching Catalogs with Simple Cone Search Services
===================================================

Owing in part to its simplicity, Simple Cone Search (SCS) services are
the most prevalent of the data access services in the VO.  It is used
to select records from source and observation catalogs.  That is, 
each record in a cone-search-able catalog represents either a discreet
source in the sky or an observation; consequently, each record has a
postion associated with it.  A cone search of such a catalog returns
all records that are within some given distance of a search position
(i.e. that fall within a circle or "cone" on the sky).  

-------------------------------
The Simple Cone Search Function
-------------------------------

The :py:func:`~pyvo.conesearch` function can be used to submit
position-based catalog queries.  Here's an example that selects guide
stars from the Guide Start Catalog (v2.3) within 3 arcminutes of a
position: 

>>> url = 'http://gsss.stsci.edu/webservices/vo/ConeSearch.aspx?CAT=GSC23&'
>>> stars = vo.conesearch(url, pos=[161.265, -59.68], radius=0.05)
>>> len(stars)
525

The results table (stored in ``stars`` in the above example) must have
at least three columns:  a source or observation identifier, a right
ascension, and a declination.  Typically though, it will include any
number of other attributes of the source (we'll explore this in the
next section).  The :py:func:`~pyvo.conesearch` function provides some
coarse-grain control over how many columns are returned via its 
``verbosity`` parameter.  It takes an integer value--1, 2, or 3.  If
it is 1, the service will return the minimum set that the publisher
has decided is sufficient for describing the source or observation.  A
value of 3 returns all of the catalog's columns that are available.
So, if you are mainly just interested in source positions (say, for
example, to plot the sources over an image), you can set the
``verbosity`` parameter to zero.  If are looking for specific
characteristics of the sources, such as photometry measurements, then
you probably want to set it to 3.  If you don't set it, the service is
obligated to assume a value of 2.  

Note that supporting the ``verbosity`` parameter is optional for a
service; that is, the service is allowed to ignore the ``verbosity``
value and return all of the available columms, regardless.  

-----------------------------------
The Cone Search Results and Records
-----------------------------------

The results that come back from a cone search are wrapped as an 
:py:class:`~pyvo.dal.scs.SCSResults` object, and when we iterate
through the results, each record is provided as an 
:py:class:`~pyvo.dal.scs.SCSRecord` instance.  In addition to the
required identifier, right ascension, and declination columns, the
results table will have a number of other columns describing the
source or observation.  Using the example from the previous section,
we can see what information we have about our guide stars:

>>> stars.fieldnames()
[u'hstID', u'ra', u'dec', u'GSC1ID', u'raEpsilon', u'decEpsilon',
u'epoch', u'FpgMag', u'JpgMag', u'NpgMag', u'UMag', u'BMag', u'VMag',
u'RMag', u'IMag', u'JMag', u'HMag', u'KMag', u'FpgMagCode',
u'JpgMagCode', u'NpgMagCode', u'UMagCode', u'BMagCode', u'VMagCode',
u'RMagCode', u'IMagCode', u'JMagCode', u'HMagCode', u'KMagCode',
u'FpgMagErr', u'JpgMagErr', u'NpgMagErr', u'UMagErr', u'BMagErr',
u'VMagErr', u'RMagErr', u'IMagErr', u'JMagErr', u'HMagErr',
u'KMagErr', u'class', u'sourceStatus', u'semiMajorAxis',
u'positionangle', u'eccentricity', u'variableFlag', u'multipleFlag',
u'distance'] 
>>> stars.getdesc('IMag').description
u'I band magnitude'

For more information about inspecting the table header information,
see the about section on :ref:`sia-results`.  

Recall that the SCS standard does not mandate standardized column
names (as discussed in the section about :ref:`sia-results`); thus,
the columns will retain their original names from when they were first
published.  The :py:class:`~pyvo.dal.scs.SCSRecord` class provides
access to access to the three required columns (regardless of what
they are called) as record properties:

>>> star = stars[0]
>>> (star.id, star.ra, star.dec) 
('S4B0000701', 161.26477050781301, -59.6844291687012)

In particular, those properties are:

======================================  ==================================================================================================================
property                                description
======================================  ==================================================================================================================
:py:attr:`~pyvo.dal.scs.SCSRecord.id`   the name or identifier of the spectrum as given by
                                        the archive
--------------------------------------  ------------------------------------------------------------------------------------------------------------------
:py:attr:`~pyvo.dal.scs.SCSRecord.ra`   the IRCS right ascension of the center of the spectrum 
                                        in decimal degrees
--------------------------------------  ------------------------------------------------------------------------------------------------------------------
:py:attr:`~pyvo.dal.scs.SCSRecord.dec`  the IRCS declination of the center of the spectrum
                                        in decimal degrees            
======================================  ==================================================================================================================

--------------------------
Search and Service Classes
--------------------------

Like the other data access services, SCS also has query and service
classes (see :ref:`sia-query` and :ref:`service-objects`,
respectively):  :py:class:`~pyvo.dal.scs.SCSQuery` and 
:py:class:`~pyvo.dal.scs.SCSService`.  The search constraints that can
be set as properties on an :py:class:`~pyvo.dal.scs.SCSQuery` instance
are as follows:

.. autosummary::

   ~pyvo.dal.scs.SCSQuery.pos
   ~pyvo.dal.scs.SCSQuery.ra
   ~pyvo.dal.scs.SCSQuery.dec
   ~pyvo.dal.scs.SCSQuery.radius
   ~pyvo.dal.scs.SCSQuery.sr
   ~pyvo.dal.scs.SCSQuery.verbosity


.. _data-access-sla:

================================================
Spectral Line Transitions and Simple Line Access
================================================

If you do spectral line studies, you may on occasion need to consult a
database of spectral line transitions.  For example, if you are
planning spectral observations within an arbitrary bandpass window,
you may need to determine what lines can appear there.  A few such
databases are available in the VO as Spectral Line Access (SLA, or
sometimes called SLAP) services.  

Here's an example searching the Splatalogue database:

>>> url = 'http://find.nrao.edu/splata-slap/slap'
>>> lines = vo.linesearch(url, wavelength="0.2110/0.2120")
>>> len(lines)
54
>>> for line in lines:
...     print("{0}: {1}".format(line['molformula'], line.wavelength))
...
H(beta): 0.211086447683
H: 0.211061133375
g-CH3CH2OH: 0.211008648827
He(beta): 0.211000464262


.. note:: Because of their specialized nature, there are very few SLA
          services available and the community's experience with them is
          still low.  Consequently, you may experience service compliance
          issues, and some of the features of the :py:mod:`pyvo.dal.sla` 
          module may not work as expected with the currently available
          services. 


.. rubric:: Footnotes

.. [#f1] *UCD* stands for *unified content descriptor*.  For more
         information, see the 
         `IVOA UCD standard <http://www.ivoa.net/Documents/latest/UCD.html>`_,
         as well as the list of valid version 1+ UCDs on the 
         `CDS UCD Info page <http://cds.u-strasbg.fr/w/doc/UCD/>`_.
         Note that SIA version 1 uses the older style UCD1 labels
         described `here <http://cdsweb.u-strasbg.fr/UCD/old/>`_.
