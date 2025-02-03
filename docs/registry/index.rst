.. _pyvo-registry:

**************************
Registry (`pyvo.registry`)
**************************

This is an interface to the Virtual Observatory Registry, a collection
of metadata records of the VO's “resources” (“resource” is jargon for: a
collection of datasets, usually with a service in front of it).  For a
wider background, see `2014A&C.....7..101D`_ for the general
architecture and `2015A&C....10...88D`_ for the search interfaces.

.. _2014A&C.....7..101D: https://ui.adsabs.harvard.edu/abs/2014A%26C.....7..101D/abstract
.. _2015A&C....10...88D: https://ui.adsabs.harvard.edu/abs/2015A%26C....10...88D/abstract

There are two fundamental modes of searching in the VO:

(a) Data discovery: This is when you are looking for some sort of data
    collection based on its metadata; a classical example would be
    something like “I need redshifts of supernovae”.

(b) Service discovery: This is what you need when you want to query all
    services of a certain kind (e.g., „all spectral services claiming to
    have infrared data“), which in turn is the basis of all-VO *dataset*
    discovery (“give me all infrared spectra of 3C273”)

Both modes are supported by this module.


.. _registry-basic-interface:

Basic interface
===============


The main interface for the module is :py:meth:`pyvo.registry.search`;
the examples below assume:

.. doctest::

  >>> from pyvo import registry

This function accepts one or more search constraints, which can be
either specified using constraint objects as positional arguments or as
keyword arguments.  The following constraints are available:

* :py:class:`~pyvo.registry.Freetext` (``keywords``): one or more
  freetext words, mached in the title, description or subject of the
  resource.
* :py:class:`~pyvo.registry.Servicetype` (``servicetype``): constrain to
  one of tap, ssa, sia1, sia2, conesearch (or full ivoids for other service
  types).  This is the constraint you want
  to use for service discovery.
* :py:class:`~pyvo.registry.UCD` (``ucd``): constrain by one or more UCD
  patterns; resources match when they serve columns having a matching
  UCD (e.g., ``phot.mag;em.ir.%`` for “any infrared magnitude”).
* :py:class:`~pyvo.registry.Waveband` (``waveband``): one or more terms
  from the vocabulary at http://www.ivoa.net/rdf/messenger giving the rough
  spectral location of the resource.
* :py:class:`~pyvo.registry.Author` (``author``): an author (“creator”).
  This is a single SQL pattern, and given the sloppy practices in the
  VO for how to write author names, you should probably generously use
  wildcards.
* :py:class:`~pyvo.registry.Datamodel` (``datamodel``): one of obscore,
  epntap, or regtap: only return TAP services having tables of this
  kind.
* :py:class:`~pyvo.registry.Ivoid` (``ivoid``): exactly match a single
  IVOA identifier (that is, in effect, the primary key in the VO).
* :py:class:`~pyvo.registry.Spatial` (``spatial``): match resources
  covering, enclosed or overlapping a certain geometry
  (point, circle, polygon, or MOC). *RegTAP 1.2 Extension*
* :py:class:`~pyvo.registry.Spectral` (``spectral``): match resources
  covering a certain part of the spectrum (usually, but not limited to,
  the electromagnetic spectrum).  *RegTAP 1.2 Extension*
* :py:class:`~pyvo.registry.Temporal` (``temporal``): match resources
  covering a some point or interval in time.  *RegTAP 1.2 Extension*

Multiple constraints are combined conjunctively (”AND”).

Constraints marked with *RegTAP 1.2 Extension* are not available on all
IVOA RegTAP services (they are on pyVO's default RegTAP endpoint,
though).  Also refer to the class documentation for further caveats on
these.

Hence, to look for for resources with UV data mentioning white dwarfs
you could either run:

.. doctest-remote-data::

  >>> resources = registry.search(keywords="white dwarf", waveband="UV")

or:

.. doctest-remote-data::

  >>> resources = registry.search(registry.Freetext("white dwarf"),
  ...                             registry.Waveband("UV"))

or a mixture between the two.  Constructing using explicit
constraints is generally preferable with more complex queries.  Where
the constraints accept multiple arguments, you can pass in sequences to
the keyword arguments; for instance:

.. doctest-remote-data::

  >>> resources = registry.search(registry.Waveband("Radio", "Millimeter"),
  ...   registry.Author("%Miller%"))

is equivalent to:

.. doctest-remote-data::

  >>> resources = registry.search(waveband=["Radio", "Millimeter"],
  ...   author='%Miller%')

There is also :py:meth:`~pyvo.registry.get_RegTAP_query`, accepting the
same arguments as :py:meth:`pyvo.registry.search`.  This function simply
returns the ADQL query that search would execute.  This is may be useful
to construct custom RegTAP queries, which could then be executed on
TAP services implementing the ``regtap`` data model.


Data Discovery
==============

In data discovery, you look for resources matching your constraints and
then figure out in a second step how to query them.  For instance, to
look for resources giving redshifts in connection with supernovae,
you would say:

.. doctest-remote-data::

  >>> resources = registry.search(registry.UCD("src.redshift"),
  ...                             registry.Freetext("AGB"))

After that, ``resources`` is an instance of
:py:class:`~pyvo.registry.RegistryResults`, which you can iterate over.  In
interactive data discovery, however, it is usually preferable to use the
``to_table`` method for an overview of the resources available:

.. doctest-remote-data::

  >>> resources.to_table()  # doctest: +IGNORE_OUTPUT
  <Table length=9>
                ivoid               ...
                                    ...
                object              ...
  --------------------------------- ...
       ivo://cds.vizier/j/a+a/392/1 ...
     ivo://cds.vizier/j/a+a/566/a95 ...
      ivo://cds.vizier/j/aj/151/146 ...
      ivo://cds.vizier/j/apj/727/14 ...
  ...

And to look for tap resources *in* a specific cone, you would do

.. doctest-remote-data::

  >>> from astropy.coordinates import SkyCoord
  >>> registry.search(registry.Freetext("Wolf-Rayet"),
  ...                 registry.Spatial((SkyCoord("23d +3d"), 3), intersect="enclosed"))  # doctest: +IGNORE_OUTPUT
  <DALResultsTable length=3>
                 ivoid                ...
                                      ...
                 object               ...
  ----------------------------------- ...
      ivo://cds.vizier/j/a+a/688/a104 ...
        ivo://cds.vizier/j/apj/938/73 ...
  ivo://cds.vizier/j/other/pasa/41.84 ...

Astropy Quantities are also supported for the radius angle of a SkyCoord-defined circular region:

.. doctest-remote-data::

  >>> from astropy import units as u
  >>> registry.search(registry.Freetext("Wolf-Rayet"),
  ...                 registry.Spatial((SkyCoord("23d +3d"), 180*u.Unit('arcmin')), intersect="enclosed"))  # doctest: +IGNORE_OUTPUT
  <DALResultsTable length=3>
                 ivoid                ...
                                      ...
                 object               ...
  ----------------------------------- ...
      ivo://cds.vizier/j/a+a/688/a104 ...
        ivo://cds.vizier/j/apj/938/73 ...
  ivo://cds.vizier/j/other/pasa/41.84 ...

Where ``intersect`` can take the following values:
  * 'covers' is the default and returns resources that cover the geometry provided,
  * 'enclosed' is for services in the given region,
  * 'overlaps' returns services intersecting with the region.

The idea is that in notebook-like interfaces you can pick resources by
title, description, and perhaps the access mode (“interface”) offered.
In the list of interfaces, you will sometimes spot an ``#aux`` after a
standard id; this is a minor VO technicality that you can in practice
ignore.  For instance, you can simply construct
:py:class:`~pyvo.dal.TAPService`-s from ``tap#aux`` interfaces.

Once you have found a resource you would like to query, you can pick it
by index; however,
this will not be stable across multiple executions.
Hence, RegistryResults also supports referencing results by short name,
which is the style we recommend.  Using full ivoids is possible, too,
and safer because these are guaranteed to be unique (which short names
are not), but it is rather clunky, and in the real VO short name
collisions should be very rare.

Use the ``get_service`` method of
:py:class:`~pyvo.registry.RegistryResource` to obtain a DAL service
object for a particular sort of interface.
To query the fourth match using simple cone search, you would
thus say:

.. doctest-remote-data::

  >>> voresource = resources["J/ApJ/727/14"]
  >>> voresource.get_service(service_type="conesearch").search(pos=(257.41, 64.345), sr=0.01)
  <DALResultsTable length=1>
     _r    recno f_ID         ID          RAJ2000  ... SED  DR7  Sloan Simbad
                                            deg    ...
  float64  int32 str1       str18         float64  ... str3 str3  str5  str6
  -------- ----- ---- ------------------ --------- ... ---- ---- ----- ------
  0.000618     1    P 170938.52+642044.1 257.41049 ...  SED  DR7 Sloan Simbad

This method will raise an error if there is more than one service of the desired
type. If you know for sure that all declared conesearch will be the same, you can
safely use ``get_service(service_type='conesearch', lax=True)`` that will return
the first conesearch it finds.

However some providers provide multiple services of the same type
-- for example in VizieR you'll find one conesearch per table.
In this case, you can inspect the available `~pyvo.registry.regtap.Interface` to services with
`~pyvo.registry.RegistryResource.list_interfaces`. Then, you can refine your
instructions to `~pyvo.registry.RegistryResource.get_service` with a keyword
constraint on the description ``get_service(service_type='conesearch', keyword='sncat')``.

.. doctest-remote-data::

  >>> for interface in voresource.list_interfaces():
  ...     print(interface)
  Interface(type='tap#aux', description='', url='http://tapvizier.cds.unistra.fr/TAPVizieR/tap')
  Interface(type='vr:webbrowser', description='', url='http://vizier.cds.unistra.fr/viz-bin/VizieR-2?-source=J/ApJ/727/14')
  Interface(type='conesearch', description='Cone search capability for table J/ApJ/727/14/table2 (AKARI IRC 3-24{mu}m, and Spitzer MIPS 24/70{mu}m photometry of Abell 2255 member galaxies)', url='https://vizier.cds.unistra.fr/viz-bin/conesearch/J/ApJ/727/14/table2?')

Or construct the service object directly from the list of interfaces with:

.. doctest-remote-data::

  >>> voresource.list_interfaces()[0].to_service()
  TAPService(baseurl : 'http://tapvizier.cds.unistra.fr/TAPVizieR/tap', description : '')

The list of interfaces can also be filtered to interfaces corresponding to services of a
specific service type:

.. doctest-remote-data::

  >>> voresource.list_interfaces("tap")
  [Interface(type='tap#aux', description='', url='http://tapvizier.cds.unistra.fr/TAPVizieR/tap')]

To operate TAP services, you need to know what tables make up a
resource; you could construct a TAP service and access its ``tables``
attribute, but you can take a shortcut and call a RegistryResource's
``get_tables`` method for a rather similar result:

.. doctest-remote-data::

  >>> tables = resources["J/ApJ/727/14"].get_tables()  # doctest: +IGNORE_WARNINGS
  >>> list(tables.keys())
  ['J/ApJ/727/14/table2']
  >>> sorted(c.name for c in tables["J/ApJ/727/14/table2"].columns)
  ['[24]', '[70]', 'dej2000', 'dr7', 'e_[24]', 'e_[70]', 'e_l15', 'e_l24', 'e_n3', 'e_n4', 'e_s11', 'e_s7', 'f_id', 'gmag', 'id', 'imag', 'l15', 'l24', 'n3', 'n4', 'raj2000', 'recno', 'rmag', 's11', 's7', 'sed', 'simbad', 'sloan', 'umag', 'y03', 'z', 'zmag']


In this case, this is a table with one of VizieR's somewhat funky names.
To run a TAP query based on this metadata, do something like:

.. doctest-remote-data::

  >>> resources["J/ApJ/727/14"].get_service(service_type="tap#aux").run_sync(
  ...   'SELECT id, z FROM "J/ApJ/727/14/table2" WHERE z>0.09 and umag<18')
  <DALResultsTable length=1>
          ID            z
        object       float64
  ------------------ -------
  171319.90+635428.0 0.09043

A special sort of access mode is ``web``, which represents some facility related
to the resource that works in a web browser.  You can ask for a
“service” for it, too; you will then receive an object that has a
``search`` method, and when you call it, a browser window should open
with the query facility (this uses python's ``webbrowser`` module):

.. doctest-skip::

  >>> resources["J/ApJ/727/14"].get_service(service_type="web").search()  # doctest: +IGNORE_OUTPUT

Note that for interactive data discovery in the VO Registry, you may
also want to have a look at Aladin's discovery tree, TOPCAT's VO menu,
or at services like DataScope_ or WIRR_ in your web browser.

.. _DataScope: https://heasarc.gsfc.nasa.gov/cgi-bin/vo/datascope/init.pl
.. _WIRR: https://dc.g-vo.org/WIRR


Service Discovery
=================

Service discovery is what you want typically in connection with a search
for datasets, as in “Give me all infrared spectra of Bellatrix“.  To do
that, you want to run the same DAL query against all the services of a
given sort.  This means that you will have to include a ``servicetype``
constraint such that all resources in your registry results can be
queried in the same way.

When that is the case, you can use each
RegistryResource's ``service`` attribute, which contains a DAL service
instance.  The opening example could be written like this:

.. This one is too expensive to run as part of CI/testing
.. doctest-skip::

  >>> from astropy.coordinates import SkyCoord
  >>> my_obj = SkyCoord.from_name("Bellatrix")
  >>> for res in registry.search(waveband="infrared", servicetype="ssap"):
  ...     print(res.service.search(pos=my_obj, size=0.001))
  ...

In reality, you will have to add some error handling to this kind of
all-VO queries: in a wide and distributed network, some service is
always down.  See `Appendix: Robust All-VO Queries`_.

The central point is: With a ``servicetype`` constraint,
each result has a well-defined ``service`` attribute that contains some
subclass of dal.Service and that can be queried in a uniform fashion.

TAP services may provide tables in well-defined data models, like
EPN-TAP or obscore.  These can be queried in similar loops, although
in some cases you will have to adapt the queries to the resources found.

In the obscore case, an all-VO query would look like this:

.. Again, that's too expensive for CI/testing
.. doctest-skip::

  >>> for svc_rec in registry.search(datamodel="obscore"):
  ...     print(svc_rec.service.run_sync(
  ...           "SELECT DISTINCT dataproduct_type FROM ivoa.obscore"))


Again, in production this needs explicit handling of failing services.
For an example of how this might look like, see `GAVO's plate tutorial`_

.. _GAVO's plate tutorial: http://docs.g-vo.org/gavo_plates.pdf

More examples
-------------

Discover archives
^^^^^^^^^^^^^^^^^

You can use the registry ``search`` method (or the ``regsearch`` function)
to discover archives that may have x-ray images and then query those archives
to find what x-ray images that have of CasA. For the arguments you will
enter ``'image'`` for the service type and ``'x-ray'`` for the waveband.
The position is provided by the Astropy library.

The query returns a :py:class:`~pyvo.registry.RegistryResults` object
which is a container holding a table of matching services. In this example
it returns 33 matching services.

.. doctest-remote-data::

  >>> import pyvo as vo
  >>> from astropy.coordinates import SkyCoord
  >>>
  >>> import warnings
  >>> warnings.filterwarnings('ignore', module="astropy.io.votable.*")
  >>>
  >>> archives = vo.regsearch(servicetype='sia1', waveband='x-ray')
  >>> pos = SkyCoord.from_name('Cas A')
  >>> len(archives)   # doctest: +IGNORE_OUTPUT
  33

There are also other type of services that you can choose via the
``servicetype`` parameter, for more details see :py:class:`~pyvo.registry.Servicetype`.

You can learn more about the archives by printing their titles
and access URL:

.. doctest-remote-data::

  >>> for service in archives:
  ...     print(service.res_title, service.access_url)  # doctest: +IGNORE_OUTPUT
  Chandra X-ray Observatory Data Archive https://cda.harvard.edu/cxcsiap/queryImages?
  Chandra Source Catalog Release 1 http://cda.cfa.harvard.edu/csc1siap/queryImages?
  ...

It is not necessary to keep track of the URL because you can search
images directly from the registry record, for example using the Chandra
X-ray Observatory (CDA) service and the ``search`` method, inserting
the position and size for the desired object.

.. doctest-remote-data::

  >>> images = archives["CDA"].search(pos=pos, size=0.25)
  >>> len(images)   # doctest: +IGNORE_OUTPUT
  822

Sometimes you are looking for a type of object. For this purpose, the
``keywords`` parameter is useful here. For example, you want to find
all catalogs related to blazars observed with Fermi:

.. doctest-remote-data::

  >>> cats = vo.regsearch(keywords=['blazar', 'Fermi'])
  >>> len(cats)   # doctest: +IGNORE_OUTPUT
  551

Or you already know the particular catalog but not the base URL for
that service. For example, you want to get cutout images from the
NRAO VLA Sky Survey (NVSS):

.. doctest-remote-data::

  >>> colls = vo.regsearch(keywords=['NVSS'], servicetype='sia1')
  >>> for coll in colls:
  ...     print(coll.res_title, coll.access_url)
  NRA) VLA Sky Survey https://skyview.gsfc.nasa.gov/cgi-bin/vo/sia.pl?survey=nvss&
  Sydney University Molonglo Sky Survey https://skyview.gsfc.nasa.gov/cgi-bin/vo/sia.pl?survey=sumss&


Search results
==============

What is coming back from registry.search is
:py:class:`pyvo.registry.RegistryResults` which is rather
similar to :ref:`pyvo-resultsets`; just remember that for interactive
use there is the ``to_tables`` method discussed above.

The individual items are instances of
:py:class:`~pyvo.registry.RegistryResource`, which expose many
pieces of metadata (e.g., title, description, creators, etc) in
attributes named like their RegTAP counterparts (see the class
documentation).  Some attributes deserve a second look.

.. doctest-remote-data::

  >>> import pyvo as vo
  >>> colls = vo.regsearch(keywords=["NVSS"], servicetype='sia1')
  >>> nvss = colls["NVSS"]
  >>> nvss.res_title
  'NRA) VLA Sky Survey'

If you are looking for a particular data collection or catalog, as
we did above when we looked for the NVSS archive, often simply
reviewing the titles is sufficient. Other times, particularly when
you are not sure what you are looking for, it helps to look deeper.

A selection of the resource metadata, including the title, shortname and
description, can be printed out in a summary form with
the ``describe`` function.

.. doctest-remote-data::

  >>> nvss.describe(verbose=True)
  NRA) VLA Sky Survey
  Short Name: NVSS
  IVOA Identifier: ivo://nasa.heasarc/skyview/nvss
  Access modes: sia
  - sia: https://skyview.gsfc.nasa.gov/cgi-bin/vo/sia.pl?survey=nvss&
  ...

The verbose option in ``describe`` will output more information about
the content of the resource, if available. Possible added entries are
the authors of the resource, an associated DOI, an url where more
information is provided, or a reference to a related paper.

The method ``service`` will, for resources that only have a single
capability, return a DAL service object ready for querying using the
respective protocol.  You should only use that attribute when the
original registry query constrained the service type, because otherwise
there is no telling what kind of service you will get back.

.. doctest-remote-data::

  >>> nvss = colls["NVSS"].service  # converts record to service object
  >>> nvss.search(pos=(350.85, 58.815),size=0.25,format="image/fits")
  <DALResultsTable length=1>
  Survey    Ra   ... LogicalName
  object float64 ...    object
  ------ ------- ... -----------
    nvss  350.85 ...           1

With this service object, we can either call its ``search`` function
directly or create query objects to get cutouts for a whole list of
sources.

.. doctest-remote-data::

  >>> cutouts1 = nvss.search(pos=(148.8888, 69.065), size=0.2)
  >>> nvssq = nvss.create_query(size=0.2)  # or create a query object
  >>> nvssq.pos = (350.85, 58.815)
  >>> cutouts2 = nvssq.execute()

Our discussion of service metadata offers an opportunity to highlight
another important property, the service's *IVOA Identifier* (sometimes
referred to as its *ivoid*).  This is a globally-unique identifier
that takes the form of a
`URI <http://en.wikipedia.org/wiki/Uniform_resource_identifier>`_:

.. doctest-remote-data::

  >>> colls = vo.regsearch(keywords=["NVSS"], servicetype='sia1')
  >>> for coll in colls:
  ...     print(coll.ivoid)
  ivo://nasa.heasarc/skyview/nvss
  ivo://nasa.heasarc/skyview/sumss

This identifier can be used to retrieve a specific service from the
registry.

.. doctest-remote-data::

  >>> nvss = vo.registry.search(ivoid='ivo://nasa.heasarc/skyview/nvss')[0].get_service(service_type='sia1')
  >>> nvss.search(pos=(350.85, 58.815),size=0.25,format="image/fits")
  <DALResultsTable length=1>
  Survey    Ra   ... LogicalName
  object float64 ...    object
  ------ ------- ... -----------
    nvss  350.85 ...           1

When the registry query did not constrain the service type, you can use
the ``access_modes`` method to see what capabilities are available.  For
instance with this identifier:

.. doctest-remote-data::

  >>> res = registry.search(ivoid="ivo://org.gavo.dc/flashheros/q/ssa")[0]
  >>> res.access_modes()  # doctest: +IGNORE_OUTPUT
  {'ssa', 'datalink#links-1.0', 'tap#aux', 'web', 'soda#sync-1.0'}

– this service can be accessed through SSA, TAP, a web interface, and
two special capabilities that pyVO cannot produce services for (mainly
because standalone service objects do not make much sense for them).

To obtain a service for one of the access modes pyVO does support, use
``get_service(service_type=mode)``.  For ``web``, this returns an object
that opens a web browser window when its ``query`` method is called.

RegistryResources also have a ``get_contact`` method.  Use this if the
service is down or seems to have bugs; you should in general get at
least an e-Mail address:

.. doctest-remote-data::

  >>> res.get_contact()
  'GAVO Data Centre Team (+49 6221 54 1837) <gavo@ari.uni-heidelberg.de>'

Finally, the registry has an idea of what kind of tables are published
through a resource, much like the VOSI tables endpoint (as a matter of
fact, the Registry should contain exactly what is there, as VOSI tables
in effect just gives a part of the registry record).  Not all publishers
properly provide table metadata to the Registry, though, but most do these days,
and then you can run:

.. doctest-remote-data::

  >>> res.get_tables()  # doctest: +IGNORE_OUTPUT
  {'flashheros.data': <VODataServiceTable name="flashheros.data">... 29 columns ...</VODataServiceTable>, 'ivoa.obscore': <VODataServiceTable name="ivoa.obscore">... 0 columns ...</VODataServiceTable>}


Alternative Registries
======================

There are several RegTAP services in the VO.  PyVO by default uses the
one at the TAP access URL http://reg.g-vo.org/tap.  You can use
alternative ones, for instance, because they are nearer to you or
because the default endpoint is down.

You can pre-select the URL by setting the ``IVOA_REGISTRY`` environment
variable to the TAP access URL of the service you would like to use.  In
a bash-like shell, you would say::

  export IVOA_REGISTRY="http://vao.stsci.edu/RegTAP/TapService.aspx"

before starting python (or the notebook processor).

Within a Python session, you can use the
`pyvo.registry.choose_RegTAP_service` function, which also takes the
TAP access URL.

As long as you have on working registry endpoint, you can find the other
RegTAP services using:

.. We probably shouldn't test the result of the next code block; this
   will change every time someone registers a new RegTAP service...

.. doctest-remote-data::

  >>> res = registry.search(datamodel="regtap")
  >>> print("\n".join(sorted(r.get_interface(service_type="tap", lax=True).access_url
  ...   for r in res)))
  http://dc.g-vo.org/tap
  http://gavo.aip.de/tap
  http://voparis-rr.obspm.fr/tap
  https://vao.stsci.edu/RegTAP/TapService.aspx



Reference/API
=============

.. automodapi:: pyvo.registry
.. automodapi:: pyvo.registry.regtap
.. automodapi:: pyvo.registry.rtcons


Appendix: Robust All-VO Queries
===============================

The VO contains many services, and even if all of them had 99.9% uptime
(which not all do), at any time you would always see failures, some of
them involving long timeouts.  Hence, if you run all-VO queries, you
should catch errors and, at least in interactive sessions, provide some
way to interrupt overly long queries.  Here is an example for how to
query all obscore services; remove the ``break`` at the end of the loop
to actually do the global query (it's there so that you don't blindly
run all-VO queries without reading at least this sentence):

.. doctest-remote-data::

   >>> from astropy.table import vstack
   >>> from pyvo import registry
   >>>
   >>> QUERY = "SELECT TOP 1 s_ra, s_dec from ivoa.obscore"
   >>>
   >>> results = []
   >>> for i, svc_rec in enumerate(registry.search(datamodel="obscore", servicetype="tap")):
   ...       # print("Querying {}".format(svc_rec.res_title))
   ...       try:
   ...           svc = svc_rec.get_service(service_type="tap", lax=True)
   ...           results.append(
   ...               svc.run_sync(QUERY).to_table())
   ...       except KeyboardInterrupt:
   ...           # someone lost their patience with a service.  Query next.
   ...           pass
   ...       except Exception as msg:
   ...           # some service is broken; you *should* complain, but
   ...           #print("  Broken: {} ({}).  Complain to {}.\n".format(
   ...           pass #    svc_rec.ivoid, msg, svc_rec.get_contact()))
   ...       if i == 2:
   ...           break
   >>> total_result = vstack(results)  # doctest: +IGNORE_WARNINGS
   >>> total_result  # doctest: +IGNORE_OUTPUT
   <Table length=5>
          s_ra               s_dec
          deg                 deg
        float64             float64
   ------------------ -------------------
             350.4619            -9.76139
     208.360833592735    52.3611106494996
     148.204840298431    29.1690999975089
           243.044008          -51.778222
   321.63278049999997 -54.579285999999996

Note that even this is not enough to reliably cover use cases like „give
me all images of M1 in the X-Ray in the VO“.  In some future version,
pyVO will come with higher-level functionality for such tasks.
