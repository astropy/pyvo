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

.. note:: As of this writing, the VO standards for searching
          registries are evolving, and a new set of standards are
          expected.  Consequently, the :py:mod:`pyvo.registry` module will
          be evolving as well.  Currently, the module only supports
          searches the `VAO Registry <http://vao.stsci.edu/directory>`_
          operated by the 
          `Virtual Astronomical Observatory (VAO) <http://www.usvao.org>`_
          project using its custom interfaces.  This implementation is 
          found in the :py:mod:`pyvo.registry.vao` sub-module.
          Support for standard interfaces is planned for future
          releases.  

.. _simple-discovery:

========================
Simple Service Discovery
========================

The most common use of the registry is to find archives with 
:ref:`VO data access services <data-access>`, and the simplest way
to do this is to use the 
:py:func:`~pyvo.regsearch` function.  For example, to find data
collections that contain searchable X-ray images:

>>> imcolls = vo.regsearch(servicetype='image', waveband='xray')
>>> imarchs.nrecs
20

Aha!  Perhaps you didn't realize there were that many.  What
collections are these?

>>> for coll in imcolls:
...     print coll.title
SIA Service for ROSAT Archive
Chandra Transmission Grating Catalog and Archive, Simple Image Access Interface
Mining the HEAVENS with the Virtual Observatory
SkyView Virtual Observatory
ROSAT All-Sky X-ray Survey
ROSAT All-Sky X-ray Background Survey: Band
Swift BAT All-Sky Survey: keV
GRANAT/SIGMA
HEAO 1A
ROSAT High Resolution Image Pointed Observations Mosaic: Intensity
INTEGRAL/Spectral Imager Galactic Center Survey
Nine Year INTEGRAL IBIS keV Galactic Plane Survey:
PSPC summed pointed observations, 1 degree cutoff,
PSPC summed pointed observations, 2 degree cutoff,
PSPC summed pointed observations, 0.6 degree cutoff,
ROSAT All-Sky X-ray Survey Band:
RXTE Allsky keV
The NASA/IPAC Extragalactic Database Image Data Atlas
Chandra Source Catalog
Chandra X-ray Observatory Data Archive

As you can gather, each record in the registry search results
represents a different service (in this case, an image service).
Included in the record is the all-important base URL for the service:  

>>> imcolls[0].accessurl
'http://www.g-vo.org/rosat/SIAP?action=queryImage&siap=siap.service.rosat&'

However, it's not necessary to keep track of that URL because you can
now search that collection directly via the registry record:

>>> images = imcolls[0].search(pos=(350.85, 58.815), size=0.25)
>>> images.nrecs
82

(See :ref:`data-access-sia` to learn what to do with image search
results.)

Other types of services via the ``servicetype`` parameter:

=========================  =======================================
set ``servicetype`` to...  ...to find:
=========================  =======================================
image                      Simple Image Access (SIA) services
spectrum                   Simple Spectral Access (SSA) services
catalog                    Simple Cone Search (SCS) services
line                       Simple Line Access (SLA) services
=========================  =======================================

.. raw:: html

   <br>
   
For example, to find all known Cone Search services:

>>> cats = vo.regsearch(servicetype='catalog')
>>> cats.nrecs
13819

Wow, that's a lot of catalogs.  (Most of these are from the
`Vizier Catalog Archive <http://vizier.u-strasbg.fr/viz-bin/VizieR>`_;
every Vizier catalog that includes a position is available as a Cone
Search service.)  For just catalogs related to blazars:

>>> cats = vo.regsearch('blazar', servicetype='catalog')
>>> cats.nrecs
93

How about blazars observed with Fermi?

>>> cats = vo.regsearch(['blazar', 'Fermi'], servicetype='catalog')
>>> cats.nrecs
5
>>> for cat in cats:
...     print cat.title
SED of the Fermi blazars (Li+, 2010)
SED of Fermi bright blazars (Abdo+, 2010)
FERMI LAT detected blazars (Abdo+, 2009)
FERMI LAT detected blazars (Abdo+, 2009)
Gamma-ray light curves of Fermi blazars (Abdo+, 2010)

Note that if you do not include the ``servicetype`` parameter, you
will get lots of result records that are *not* data access services.
A VO registry many different kinds of records in its database,
including other types of services, data collections, organizations,
and even other registries.  Together, we generically refer to these as
*VO resources*.  

Sometimes you may be looking for a particular catalog or image collections
that you already know exists, and you just need to learn the base URL
for the service.  The ``keywords`` parameter can be used to find it.
For example, suppose you want to get cutout images from the NRAO VLA
Sky Survey (NVSS):

>>> colls = vo.regsearch(keywords="NVSS", servicetype='image')
>>> for coll in colls:
...     print coll.title
NVSS
Sydney University Molonglo Sky Survey

Obviously, the first record is the NVSS image archive.  The SUMSS
collection was matched as well because its description in the registry
happens to include the string, "NVSS".  

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
:py:class:`~pyvo.registry.vao.RegistryResults` instance, and each
record is represented as a
:py:class:`~pyvo.registry.vao.SimpleResource` instance. 

A :py:class:`~pyvo.registry.vao.SimpleResource` record acts like a
dictionary where the keys are the column names from the results table;
using our NVSS example from the previous section,

>>> nvss = colls[0]
>>> nvss.keys()
('tags', 'shortName', 'title', 'description', 'publisher', 'waveband',
'identifier', 'updated', 'subject', 'type', 'contentLevel', 'regionOfRegard', 
'version', 'resourceID', 'capabilityClass', 'capabilityStandardID', 
'capabilityValidationLevel', 'interfaceClass', 'interfaceVersion', 
'interfaceRole', 'accessURL', 'maxRadius', 'maxRecords', 'publisherID',
'referenceURL') 
>>> nvss['waveband']
('Radio',)

Some of the more useful items are available as properties:

=========================================================   ================================================================================================================================================================================================================================================================
:py:attr:`~pyvo.registry.vao.SimpleResource.accessurl`      the base URL that can be used to access the service
:py:attr:`~pyvo.registry.vao.SimpleResource.capability`     the type of service (using its IVOA capability name) 
:py:attr:`~pyvo.registry.vao.SimpleResource.contentlevel`   a list of labels indicating the intended audiences
:py:attr:`~pyvo.registry.vao.SimpleResource.description`    a paragraph's worth of text describing the data provided by the service
:py:attr:`~pyvo.registry.vao.SimpleResource.identifier`     the globally-unique IVOA identifier for the service
:py:attr:`~pyvo.registry.vao.SimpleResource.ivoid`          synonym for :py:attr:`~pyvo.registry.vao.SimpleResource.identifier`
:py:attr:`~pyvo.registry.vao.SimpleResource.publisher`      the name of the organization responsible for providing this service.
:py:attr:`~pyvo.registry.vao.SimpleResource.shortname`      the short name or abbreviation for the data collection and/or service
:py:attr:`~pyvo.registry.vao.SimpleResource.standardid`     the IVOA identifier of the service standard it supports
:py:attr:`~pyvo.registry.vao.SimpleResource.subject`        a list of the subject keywords that describe this service and the data it contains
:py:attr:`~pyvo.registry.vao.SimpleResource.tags`           a list of user-friendly labels identifying the type of service it is
:py:attr:`~pyvo.registry.vao.SimpleResource.title`          the title of the data collection or service
:py:attr:`~pyvo.registry.vao.SimpleResource.type`           a list of the resource types that characterize this service
:py:attr:`~pyvo.registry.vao.SimpleResource.waveband`       a list of names of the spectral wavebands covered by the data offered by the service
=========================================================   ================================================================================================================================================================================================================================================================

.. raw:: html

   <br>
   
If you are looking for a particular data collection or catalog, as we
did above when we looked for the NVSS archive, often simply reviewing
the titles is sufficient.  Other times, particularly when you are not
sure what you are looking for, it helps to look deeper.  

The resource description, available via the 
:py:attr:`~pyvo.registry.vao.SimpleResource.description` property,
tends to be the most revealing.  It contains a paragraph (or two)
summarizing the catalog or data collection.  It will often describe
the scientific intent behind the collection.  

The :py:attr:`~pyvo.registry.vao.SimpleResource.publisher`, which
names the organization that deployed the service, can also be
helpful.  Often a popular data collection or catalog will be mirrored
at a variety of sites; the
:py:attr:`~pyvo.registry.vao.SimpleResource.publisher` can reveal
where the collection is located.  

The :py:attr:`~pyvo.registry.vao.SimpleResource.shortname` can also be
helpful, as well.  This name is meant to be short--16 characters or
fewer; consequently, the value is often includes the abbreviation for the
project or observatory that produced the collection or catalog.  

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
most important function is to provide remember the base URL for the
service to allow us to query it without having to pass around the URL
directly.  Further, in the section, :ref:`service-objects`, we saw how
we can create service objects directly from a registry search record.
Here's a refresher example, based on the NVSS example from the
previous section:

>>> nvss = colls[0].to_service()  # converts record to serviec object
>>> nvss.baseurl
'http://skyview.gsfc.nasa.gov/cgi-bin/vo/sia.pl?survey=nvss&'
>>> nvss.shortname
'NVSS'
>>> nvss.info.keys()
('tags', 'shortName', 'title', 'description', 'publisher', 'waveband',
'identifier', 'updated', 'subject', 'type', 'contentLevel', 'regionOfRegard', 
'version', 'resourceID', 'capabilityClass', 'capabilityStandardID', 
'capabilityValidationLevel', 'interfaceClass', 'interfaceVersion', 
'interfaceRole', 'accessURL', 'maxRadius', 'maxRecords', 'publisherID',
'referenceURL') 

Thus, not only does this service instance contain the base URL but it
also includes all of the metadata from the registry that desribes the
service.  

Retrieving a Service By Its Identifier
--------------------------------------

Our discussion of service metadata offers an opportunity to highlight
another important property, the service's *IVOA Identifier* (sometimes
referred to as its *ivoid*).  This is a globally-unique identifier
that takes the form of a 
`URI <http://en.wikipedia.org/wiki/Uniform_resource_identifier>`_:

>>> colls = vo.regsearch(keywords="NVSS", servicetype='image')
>>> for coll in colls:
...     print coll.identifier
ivo://nasa.heasarc/skyview/nvss#1
ivo://nasa.heasarc/skyview/sumss#1

This identifier can be used to uniquely retrieve a service desription
from the registry.  

This is a good time to note that the registry has an associated
service class, too: :py:class:`~pyvo.registry.vao.RegistryService`.
It behaves much like other service classes (e.g. you can create
:py:class:`~pyvo.registry.vao.RegistryQuery` instances from it with
its :py:meth:`~pyvo.registry.vao.create_query` method), but it
provides a :py:meth:`~pyvo.registry.vao.resolve2service` method that
can resolve an IVOA identifier directly into a service object:

>>> reg = vo.registry.RegistryService()
>>> nvss = reg.resolve2service('ivo://nasa.heasarc/skyview/nvss#1')
>>> nvss.title, nvss.baseurl
('NVSS', 'http://skyview.gsfc.nasa.gov/cgi-bin/vo/sia.pl?survey=nvss&')
>>> # search the service in one call
>>> cutouts1 = nvss.search(pos=(148.8888, 69.065) size=0.2)
>>> nvssq = nvss.create_query(size=0.2)  # or create a query object
>>> nvss.pos = (350.85, 58.815)
>>> cutouts2 = nvss.execute()

If you want to keep a reference to a single service (say, as part of a
list of favorite services), it is better to save the identifier than
the base URL.  Over time, a service's base URL can change; however,
the identifier will stay the same.  

As we end this discussion of the service objects, you can hopefully
see that there is a straight-forward chain of discovery classes that
connect the registry down through to a dataset.  Spelled out in all
its detail, it looks like this:

.. code-block:: python

   reg = vo.registry.RegistryService()         # RegistryService
   rq = reg.create_query(keywords="NVSS", 
                         servicetype='image')  # RegistryQuery
   colls = rq.execute()                        # RegistryResults
   nvss = colls[0]                             # SimpleResource
   nvss = colls[0].to_service()                # SIAService
   nq = nvss.create_query(pos=(350.85, 58.815),
                          size=0.25, 
                          format="image/fits") # SIAQuery
   images = nq.execute()                       # SIAResults
   firstim = images[0]                         # SIARecord
   firstim.cachedataset()           # a FITS file saved to disk!

Most of the time, it's not necessary to follow all these steps
yourself, so there are functions and methods that provide syntactic
shortcuts.  However, when you need some finer control over the
process, it is possible to jump off the fast track and work directly
with an underlying object.  

.. _reg-tips:

============================================
Tips for Accessing the Registry from Scripts 
============================================



