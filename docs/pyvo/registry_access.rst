.. _registry-access:

***************************************
Discovering Services with a VO Registry
***************************************

In the preceding section, :ref:`data-access`, we showed how you could
retrieve data from various archives using standard VO services they
provide.  To search a particular archive, one needs the *base URL* of
that archives service.  This section shows how to discover VO services
(and their base URLs) using what is known as a *VO Registry service*.  

A *VO Registry* is a on-line database of all data collections and
services know to the Virtual Observatory.  Using the 
:py:mod:`pyvo.registry` module, you can search discover archive
services based on type, waveband, and topic keywords.  

.. _simple-discovery:

========================
Simple Service Discovery
========================

The most common use of the registry is to find archives with 
:ref:`VO data access services <data-access>`, and the simplest way
to do this is to use the 
:py:func:`~pyvo.regsearch` function.  For example, to find data
collections that contain searchable infrared images:

>>> services = vo.regsearch(servicetype='sia', waveband='infrared')
>>> len(services)
15

Aha! Perhaps you didn't realize there were that many.
What collections are these?

>>> for service in services:
... print coll.title
Chandra X-ray Observatory Data Archive
Chandra Source Catalog
Swift BAT All-Sky Survey:   keV
GRANAT/SIGMA
HEAO 1A
ROSAT High Resolution Image Pointed Observations Mosaic: Intensity
INTEGRAL/Spectral Imager Galactic Center Survey
Nine Year INTEGRAL IBIS  keV Galactic Plane Survey:
PSPC summed pointed observations, 1 degree cutoff,
PSPC summed pointed observations, 2 degree cutoff,
PSPC summed pointed observations, 0.6 degree cutoff,
ROSAT All-Sky X-ray Survey  Band:
ROSAT All-Sky X-ray Background Survey: Band
RXTE Allsky  keV
ROSAT Survey and Pointed Images

As you can gather, each record in the registry search results
represents a different service (in this case, an image service).
Included in the record is the all-important base URL for the service:

>>> services[0].access_url
'http://cda.harvard.edu/cxcsiap/queryImages?'

However, it's not necessary to keep track of that URL because you can
now search that collection directly via the registry record:

>>> images = services[0].search(pos=(350.85, 58.815), size=0.25)
>>> len(images)
474

(See :ref:`data-access-sia` to learn what to do with image search
results.)

Other types of services via the ``servicetype`` parameter:

+---------------------------+----------------------------------------+
| set ``servicetype`` to... | ...to find:                            |
+===========================+========================================+
| sia                       | Simple Image Access (SIA) services     |
+---------------------------+----------------------------------------+
| ssa                       | Simple Spectral Access (SSA) services  |
+---------------------------+----------------------------------------+
| conesearch                | Simple Cone Search (SCS) services      |
+---------------------------+----------------------------------------+
| slap                      | Simple Line Access (SLA) services      |
+---------------------------+----------------------------------------+
| tap                       | Table Access Protocol (TAP) services   |
+---------------------------+----------------------------------------+

.. raw:: html

   <br>
   
For example, to find all known Cone Search services:

>>> cats = vo.regsearch(servicetype='conesearch')
>>> len(cats)
18189

Wow, that's a lot of catalogs.  (Most of these are from the
`Vizier Catalog Archive <http://vizier.u-strasbg.fr/viz-bin/VizieR>`_;
every Vizier catalog that includes a position is available as a Cone
Search service.)  For just catalogs related to blazars:

>>> cats = vo.regsearch(keywords=['blazar'], servicetype='conesearch')
>>> len(cats)
146

How about blazars observed with Fermi?

>>> cats = vo.regsearch(keywords=['blazar', 'Fermi'], servicetype='conesearch')
>>> len(cats)
244

Sometimes you may be looking for a particular catalog or image collections
that you already know exists, and you just need to learn the base URL
for the service.  The ``keywords`` parameter can be used to find it.
For example, suppose you want to get cutout images from the NRAO VLA
Sky Survey (NVSS):

>>> colls = vo.regsearch(keywords=["NVSS"], servicetype='sia')
>>> for coll in colls:
...     print coll.res_title
NVSS
Sydney University Molonglo Sky Survey

Obviously, the first record is the NVSS image archive.  The SUMSS
collection was matched as well because its description in the registry
happens to include the string, "NVSS".  

If you want to limit the search results to a certain datamodel, include the
``datamodel`` parameter:

>>> obscores = vo.regsearch(datamodel="obscore")

.. _reg-results:

===========================
Registry Search Result Data
===========================

As you can see from the examples above, a search will often return
more than one record, and so sometimes you need to review some of the
resource metadata to determine which one or ones you want.  You may
have noticed that the results behave similarly to the results from the
data access services (see :ref:`data-access-sia`).  Like them,
registry search results are returned as a 
:py:class:`~pyvo.registry.regtap.RegistryResults` instance, and each
record is represented as a
:py:class:`~pyvo.registry.regtap.RegistryResource` instance. 

A :py:class:`~pyvo.registry.regtap.RegistryRecord` record acts like a
dictionary where the keys are the column names from the results table;
using our NVSS example from the previous section,

>>> nvss = colls[0]
>>> nvss.keys()
['cap_index', 'res_description', 'intf_type', 'standard_id', 'cap_index_',
 'url_use', 'res_type', 'intf_role', 'cap_description', 'wsdl_url',
 'source_format', 'res_version', 'ivoid__', 'content_level', 'source_value',
 'std_version', 'updated', 'short_name', 'query_type', 'creator_seq',
 'intf_index', 'content_type', 'harvested_from', 'res_title',
 'region_of_regard', 'created', 'rights', 'waveband', 'reference_url', 'ivoid',
 'cap_type', 'access_url', 'ivoid_', 'result_type']
>>> nvss['waveband']
('Radio',)

Some of the more useful items are available as properties:

==================================================================  ==========================================================================================================================================================================
:py:attr:`~pyvo.registry.regtap.RegistryResource.ivoid`             the IVOA identifier for the resource.
:py:attr:`~pyvo.registry.regtap.RegistryResource.res_type`          the resource types that characterize this resource.
:py:attr:`~pyvo.registry.regtap.RegistryResource.short_name`        the short name for the resource 
:py:attr:`~pyvo.registry.regtap.RegistryResource.res_title`         the title of the resource
:py:attr:`~pyvo.registry.regtap.RegistryResource.content_levels`    a list of content level labels that describe the intended audience for this resource.
:py:attr:`~pyvo.registry.regtap.RegistryResource.res_description`   the textual description of the resource.
:py:attr:`~pyvo.registry.regtap.RegistryResource.reference_url`     URL pointing to a human-readable document describing this resource.
:py:attr:`~pyvo.registry.regtap.RegistryResource.creators`          The creator(s) of the resource in the ordergiven by the resource record author
:py:attr:`~pyvo.registry.regtap.RegistryResource.content_types`     the IVOA identifier of the service standard it supports
:py:attr:`~pyvo.registry.regtap.RegistryResource.source_format`     the format of source_value.
:py:attr:`~pyvo.registry.regtap.RegistryResource.region_of_regard`  numeric value representing the angle, given in decimal degrees, by which a positional query against this resource should be "blurred" in order to get an appropriate match.
:py:attr:`~pyvo.registry.regtap.RegistryResource.waveband`          a list of names of the wavebands that the resource provides data for
:py:attr:`~pyvo.registry.regtap.RegistryResource.access_url`        the URL that can be used to access the service resource
:py:attr:`~pyvo.registry.regtap.RegistryResource.standard_id`       the IVOA standard identifier
==================================================================  ==========================================================================================================================================================================

.. raw:: html

   <br>
   
If you are looking for a particular data collection or catalog, as we
did above when we looked for the NVSS archive, often simply reviewing
the titles is sufficient.  Other times, particularly when you are not
sure what you are looking for, it helps to look deeper.  

The resource description, available via the 
:py:attr:`~pyvo.registry.regtap.ResourceRecord.res_description` property,
tends to be the most revealing.  It contains a paragraph (or two)
summarizing the catalog or data collection.  It will often describe
the scientific intent behind the collection.  

The :py:attr:`~pyvo.registry.regtap.RegistryResource.short_name` can also be
helpful, as well.  This name is meant to be short--16 characters or
fewer; consequently, the value is often includes the abbreviation for the
project or observatory that produced the collection or catalog.  

A selection of the resource metadata, including the title, shortname and
desription, can be printed out in a summary form with
the :py:meth:`~pyvo.registry.regtap.RegistryResource.describe` function.

.. code-block:: python

    >>> nvss.describe()
    Image Data Service
    NVSS
    Short Name: NVSS
    IVOA Identifier: ivo://nasa.heasarc/skyview/nvss
    Base URL: http://skyview.gsfc.nasa.gov/cgi-bin/vo/sia.pl?survey=nvss&

    The NRAO VLA Sky Survey is currently underway at the VLA and data is made
    available to the public as soon as processed.  <i> SkyView </i> has copied the
    NVSS intensity data from the NRAO FTP site.  The full NVSS survey data
    includes information on other Stokes parameters. Note that <i> SkyView </i>
    may be slightly out of date with regard to the latest releases of NVSS data.
    The current information was copied in November 1997.

    Observations for the 1.4 GHz NRAO VLA Sky Survey (NVSS) began in 1993
    September and should cover the sky north of -40 deg declination (82% of the
    celestial sphere) before the end of 1996.  The principal data products will
    be: <ol> <li> A set of 2326 continuum map "cubes," each covering 4 deg X 4 deg
    with three planes containing Stokes I, Q, and U images.  These maps were made
    with a relatively large restoring beam (45 arcsec FWHM) to yield the high
    surface-brightness sensitivity needed for completeness and photometric
    accuracy.  Their rms brightness fluctuations are about 0.45 mJy/beam = 0.14 K
    (Stokes I) and 0.29 mJy/beam = 0.09 K (Stokes Q and U).  The rms uncertainties
    in right ascension and declination vary from 0.3 arcsec for strong (S > 30
    mJy) point sources to 5 arcsec for the faintest (S = 2.5 mJy) detectable
    sources.

    <li>  Lists of discrete sources. </ol>

    The NVSS is being made as a service to the astronomical community, and the
    data products are being released as soon as they are produced and verified.
    <P> The NVSS survey is included on the <b>SkyView High Resolution Radio
    Coverage </b>map <http://skyview.gsfc.nasa.gov/images/high_res_radio.jpg>.
    This map shows coverage on an Aitoff projection of the sky in equatorial
    coordinates.

    Subjects: NVSS
    Waveband Coverage: radio



As the examples in this chapter suggest, queries to the registry are
often done interactively.  You will find the need to review the
results by eye, to further refine the collections and catalogs that
you discover.  In the 
:ref:`last section of this chapter <reg-tips>`, we present a few
tips for working with the registry within scripts in a non-interactive
context.  

.. _reg-to-service:

==============================================
Working with Service Objects from the Registry
==============================================

In the previous chapter, :ref:`data-access`, we introduced the
*Service classes* (e.g. :py:class:`~pyvo.dal.sia.SIAService`).  These
are classes whose instances represent a particular service, and its
most important function is to remember the base URL for the
service and allow us to query it without having to pass around the URL
directly.  Further, in the section, :ref:`service-objects`, we saw how
we can create service objects directly from a registry search record.
Here's a refresher example, based on the NVSS example from the
previous section:

>>> nvss = colls[0].service  # converts record to serviec object
>>> nvss.baseurl
'http://skyview.gsfc.nasa.gov/cgi-bin/vo/sia.pl?survey=nvss&'
>>> query = nvss.create_query(size=0.25, format="image/fits")

Thus, not only does this service instance contain the base URL but it
also includes all of the metadata from the registry that desribes the
service.  With this service object, we can either call its 
:py:attr:`~pyvo.dal.sia.SIAService.search` function directly or 
create query objects to get cutouts for a whole list of sources.  

.. _registry-resolve:

Retrieving a Service By Its Identifier
--------------------------------------

Our discussion of service metadata offers an opportunity to highlight
another important property, the service's *IVOA Identifier* (sometimes
referred to as its *ivoid*).  This is a globally-unique identifier
that takes the form of a 
`URI <http://en.wikipedia.org/wiki/Uniform_resource_identifier>`_:

>>> colls = vo.regsearch(keywords=["NVSS"], servicetype='sia')
>>> for coll in colls:
... print coll.identifier
ivo://nasa.heasarc/skyview/nvss
ivo://nasa.heasarc/skyview/sumss

This identifier can be used to uniquely retrieve a service desription
from the registry.  

>>> nvss = vo.registry.ivoid2service('ivo://nasa.heasarc/skyview/nvss')
>>> nvss.title, nvss.baseurl
('NVSS', 'http://skyview.gsfc.nasa.gov/cgi-bin/vo/sia.pl?survey=nvss&')
>>> # search the service in one call
>>> cutouts1 = nvss.search(pos=(148.8888, 69.065) size=0.2)
>>> nvssq = nvss.create_query(size=0.2)  # or create a query object
>>> nvssq.pos = (350.85, 58.815)
>>> cutouts2 = nvssq.execute()

.. note ::
    If you want to keep a reference to a single service (say, as part of a
    list of favorite services), it is better to save the identifier than
    the base URL.  Over time, a service's base URL can change; however,
    the identifier will stay the same.  

As we end this discussion of the service objects, you can hopefully
see that there is a straight-forward chain of discovery classes that
connect the registry down through to a dataset.  Spelled out in all
its detail, it looks like this:

.. code-block:: python

    services = vo.regsearch(keywords=["NVSS"],
                        servicetype='sia')          # RegistryResults
    nvss = services[0]                              # RegistryResource
    nvsss = nvss.service                            # SIAService
    nq = nvss.create_query(pos=(350.85, 58.815),
                        size=0.25, 
                        format="image/fits")        # SIAQuery
    images = nq.execute()                           # SIAResults
    firstim = images[0]                             # SIARecord

Most of the time, it's not necessary to follow all these steps
yourself, so there are functions and methods that provide syntactic
shortcuts.  However, when you need some finer control over the
process, it is possible to jump off the fast track and work directly
with an underlying object.  

.. _reg-tips:

============================================
Tips for Accessing the Registry from Scripts 
============================================

.. eventually we want to replace prose recipes with code (or built-in tools)

As we've seen from the examples in this chapter, discovering and
selecting services from the registry is often an interative process,
particulary when you are not sure what you are looking for and you use
the registry as a tool for exploration.  In this mode, you will find
yourself reviewing registry search results by eye to focus in on those
data collections and services of interest.  

However, there are a few use cases where non-interactive registry
queries--i.e., queries that you can run blindly from a script--work
well:

#. Taking an inventory of all data available for particular postion
   and/or topic.
#. Compiling a list of catalogs that include columns that contain particular
   kinds of data.
#. Recalling a service of set of services by their IVOA identifiers.
#. Look for new catalogs or data collections related to a particular
   topic and recently added to the VO.

The Data Inventory
------------------

The :ref:`first example <getting-started-examples>` in the chapter, 
:ref:`getting-started`, is an example of creating an inventory of a
available data.  In that case, it was an inventory of available X-ray
images of the Cas A supernova remnant.  We didn't actually download
these images; instead, we created a table describing the images along
with the URL for downloading them later, as desired.

The Hunt for Measurements
-------------------------

You may be creating your own catalog of objects selected for a
particular science study.  You may want to fill out the columns of
your source table with attributes of interest, such as photometry
measurements.  To do this, you'll need to find the catalogs that have
this data.  One simple recipe for doing this would be:

#. query the registry for all catalogs related to your science using
   the ``keywords``, ``waveband``, and ``servicetype`` as applicable.  
#. For each catalog found, run a metadata search (which just returns
   an empty table).
#. Search the columns of each table and find those where the name,
   ucd, or utype attributes contain the string "mag".

The selection of columns is somewhat crude for more detailed kinds of
data.  Using the UCD label, it's possible to identify columns with
particular kinds of magnitudes (e.g J, V, bolometric, etc.) as well as
of other types of quantities, such as redshift.  See 
the `CDS UCD Info page <http://cds.u-strasbg.fr/w/doc/UCD/>`_ for a
list of ucds that you can look for.  

Recalling a Favorite Service
----------------------------

In the previous section, :ref:`registry-resolve`, we discussed how one
might create a list of favorite services which include their IVOA
Identifiers.  Each can be resolved into a service object using the 
:py:meth:`~pyvo.registry.regtap.ivoid2service` so that
the service can be searched.  You may, for example, want to re-search
a set of archives periodically to determine if it has any new data
since the last time you checked.  

Discovering New Additions to the VO
-----------------------------------

In a similar vein, you may be interested in knowing when new catalogs
or data collections, particularly any related to a topic of interest,
become available in VO.  Here's a recipe for a script that you would
run periodically which can accomplish this: 

#. Execute a registry query that looks for potentially interesting
   catalogs and collections.  

#. Extract the list of IVOA identifiers returned in the results.

#. From disk, open the registry search results saved from the previous
   run of the script and extract the identifiers.

#. Compare the two lists of identifiers, finding those that appear in
   the new results that are not in the previous results.  These represent
   the new additions to the VO.

#. Create a union of the two search result tables and save that as the
   latest result.  

#. Report the new additions.  

