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


Basic interface
===============


The main interface for the module is :py:meth:`pyvo.registry.search`;
the examples below assume::

  >>> from pyvo import registry

This function accepts one or more search constraints, which can be
either specificed using constraint objects as positional arguments or as
keyword arguments.  The following constraints are available:

* :py:class:`pyvo.registry.Freetext` (``keywords``): one or more
  freetext words, mached in the title, description or subject of the
  resource.
* :py:class:`pyvo.registry.Servicetype` (``servicetype``): constrain to
  one of tap, ssa, sia, conesearch.  This is the constraint you want
  to use for service discovery.
* :py:class:`pyvo.registry.UCD` (``ucd``): constrain by one or more UCD
  patterns; resources match when they serve columns having a matching
  UCD (e.g., ``phot.mag;em.ir.%`` for “any infrared magnitude”).
* :py:class:`pyvo.registry.Waveband` (``waveband``): one or more terms
  from the vocabulary at http://www.ivoa.net/messenger giving the rough
  spectral location of the resource.
* :py:class:`pyvo.registry.Author` (``author``): an author (“creator”).
  This is a single SQL pattern, and given the sloppy practices in the
  VO for how to write author names, you should probably generously use
  wildcards.
* :py:class:`pyvo.registry.Datamodel` (``datamodel``): one of obscore,
  epntap, or regtap: only return TAP services having tables of this
  kind.
* :py:class:`pyvo.registry.Ivoid` (``ivoid``): exactly match a single
  IVOA identifier (that is, in effect, the primary key in the VO).
* :py:class:`pyvo.registry.Spatial` (``spatial``): match resources
  covering a certain geometry (point, circle, polygon, or MOC).
  *RegTAP 1.2 Extension*.
* :py:class:`pyvo.registry.Spectral` (``spectral``): match resources
  covering a certain part of the spectrum (usually, but not limited to,
  the electromagnetic spectrum).  *RegTAP 1.2 Extension*.

Multiple contratints are combined conjunctively (”AND”).

Constraints marked with *RegTAP 1.2 Extension* are not available on all
IVOA RegTAP services (they are on pyVO's default RegTAP endpoint,
though).  Also refer to the class documentation for further caveats on
these.

Hence, to look for for resources with UV data mentioning white dwarfs
you could either run::

  >>> registry.search(keywords="white dwarf", waveband="UV")

or::

  >>> registry.search(registry.Fulltext("white dwarf"),
  ...   registry.Waveband("UV"))

or a mixture between the two.  Constructing using explicit
constraints is generally preferable with more complex queries.  Where
the constraints accept multiple arguments, you can pass in sequences to
the keyword arguments; for instance::

  >>> registry.search(registry.Waveband("Radio", "Submillimeter"))

is equivalent to::

  >>> registry.search(waveband=["Radio", "Submillimeter"])

There is also :py:meth:`pyvo.registry.get_RegTAP_query`, accepting the
same arguments as :py:meth:`pyvo.registry.search`.  This function simply
returns the ADQL query that search would execute.  This is may be useful
to construct custom RegTAP queries, which could then be executed on
TAP services implementing the ``regtap`` data model.


Data Discovery
==============

In data discovery, you look for resources matching your constraints and
then figure out in a second step how to query them.  For instance, to
look for resources giving redshifts in connection with supernovae,
you would say::

  >>> resources = registry.search(registry.UCD("src.redshift"),
  ...   registry.Freetext("supernova"))

After that, ``resources`` is an instance of
:py:class:`pyvo.registry.RegistryResults`, which you can iterate over.  In
interactive data discovery, however, it is usually preferable to use the
``to_table`` method for an overview of the resources available::

  >>> resources.to_table()
  <Table length=158>
  index                              title                              ...        interfaces
  int32                              str67                              ...          str24
  ----- --------------------------------------------------------------- ... ------------------------
      0               Asiago Supernova Catalogue (Barbon et al., 1999-) ... conesearch, tap#aux, web
      1                   Asiago Supernova Catalogue (Version 2008-Mar) ... conesearch, tap#aux, web
      2      Sloan Digital Sky Survey-II Supernova Survey (Sako+, 2018) ... conesearch, tap#aux, web
  ...


The idea is that in notebook-like interfaces you can pick resources by
title, description, and perhaps the access mode (“interface”) offered.
In the list of interfaces, you will sometimes spot an ``#aux`` after a
standard id; this is a minor VO technicality that you can in practice
ignore.  For instance, you can simply construct
:py:class:`pyvo.dal.TAPService`-s from ``tap#aux`` interfaces.

Once you have found a resource you would like to query, pick it by index
(which will not be stable across multiple executions.
Use a resource's ivoid to identify resources over multiple runs
of a programme; cf. the :py:class:`pyvo.registry.Ivoid`
constraint).  Use the ``get_service`` method of
:py:class:`pyvo.registry.RegistryResource` to obtain a DAL service
object for a particular sort of interface.
To query the fourth match using simple cone search, you would
thus say::

  >>> resources[4].get_service("conesearch").search(pos=(120, 73), sr=1)
  <Table length=1>
     _r    recno   SN   r_SN    z       sI     e_sI     t1     e_t1     I1     e_I1     t2     e_t2     I2     e_I2    chi2    N   Simbad    _RA       _DE
    deg                                                 d       d      mag     mag      d       d      mag     mag                           deg       deg
  float64  int32  str6 uint8 float32 float32 float32 float32 float32 float32 float32 float32 float32 float32 float32 float32 int16  str6   float64   float64
  -------- ----- ----- ----- ------- ------- ------- ------- ------- ------- ------- ------- ------- ------- ------- ------- ----- ------ --------- ---------
  0.588592    19 1995E     3   0.012   1.026   0.040   0.067   0.635  15.393   0.024  26.340   0.950  16.093   0.050    6.78    14 Simbad 117.98646  73.00961


To operate TAP services, you need to know what tables make up a
resource; you could construct a TAP service and access its ``tables``
attribute, but you can take a shortcut and call a RegistryResource's
``get_tables`` method for a rather similar result::

  >>> tables = resources[4].get_tables()
  >>> list(tables.keys())
  ['J/A+A/437/789/table2']
  >>> tables['J/A+A/437/789/table2'].columns
  [<BaseParam name="recno"/>, <BaseParam name="sn"/>, <BaseParam name="r_sn"/>, <BaseParam name="z"/>, <BaseParam name="si"/>, <BaseParam name="e_si"/>, <BaseParam name="t1"/>, <BaseParam name="e_t1"/>, <BaseParam name="i1"/>, <BaseParam name="e_i1"/>, <BaseParam name="t2"/>, <BaseParam name="e_t2"/>, <BaseParam name="i2"/>, <BaseParam name="e_i2"/>, <BaseParam name="chi2"/>, <BaseParam name="n"/>, <BaseParam name="simbad"/>, <BaseParam name="_ra"/>, <BaseParam name="_de"/>]

In this case, this is a table with one of VizieR's somewhat funky names.
To run a TAP query based on this metadata, do something like::

  >>> resources[4].get_service("tap#aux").run_sync(
  ...   'SELECT sn, z FROM "J/A+A/437/789/table2" WHERE z>0.04')
  <Table length=4>
    SN      z
  object float64
  ------ -------
  1992bh   0.045
  1992bp   0.079
  1993ag   0.049
   1993O   0.051

A special sort of access mode is ``web``, which represents some facility related
to the resource that works in a web browser.  You can ask for a
“service” for it, too; you will then receive an object that has a
``search`` method, and when you call it, a browser window should open
with the query facility (this uses python's webbrowser module)::

  resources[4].get_service("web").query()

Note that for interactive data discovery in the VO Registry, you may
also want to have a look at Aladin's discovery tree, TOPCAT's VO menu,
or at services like DataScope_ or WIRR_ in your web browser.

.. _DataScope: https://heasarc.gsfc.nasa.gov/cgi-bin/vo/datascope/init.pl
.. _WIRR: https://dc.g-vo.org/WIRR


Service Discovery
=================

Service discovery is what you want typcially in connection with a search
for datasets, as in “Give me all infrared spectra of Bellatrix“.  To do
that, you want to run the same DAL query against all the services of a
given sort.  This means that you will have to include a servicetype
constraint such that all resources in your registry results can be
queried in the same way.

When that is the case, you can use each
RegistryResource's ``service`` attribute, which contains a DAL service
instance.  The opening example could be written like this::

  >>> from astropy.coordinates import SkyCoord
  >>> my_obj = SkyCoord.from_name("Bellatrix")
  >>> for res in registry.search(waveband="infrared", servicetype="spectrum"):
  ...   print(res.service.search(pos=my_obj, size=0.001))
  ...

In reality, you will have to add some error handling to this kind of
all-VO queries: in a wide and distributed network, some service is
always down.

The central point is: With a servicetype constraint, each result has
a well-defined ``service`` attribute that contains some subclass of
dal.Service and that can be queried in a uniform fashion.

TAP services may provide tables in well-defined data models, like
EPN-TAP or obscore.  These can be queried in similar loops, although
in some cases you will have to adapt the queries to the resources found.

In the obscore case, an all-VO query would look like this::

  >>> for svc_rec in registry.search(datamodel="obscore"):
  ...     print(svc_rec.service.run_sync(
  ...         "SELECT DISTINCT dataproduct_type FROM ivoa.obscore"))

Again, in production this needs explicit handling of failing services.
For an example of how this might look like, see `GAVO's plate tutorial`_

.. _GAVO's plate tutorial: http://docs.g-vo.org/gavo_plates.pdf

Search results
==============

What is coming back from registry.search is rather similar to
:ref:`pyvo-resultsets`; just remember that for interactive use there is
the ``to_tables`` method discussed above.

The individual items are instances of
:py:class:`pyvo.registry.regtap.RegistryResource`, which expose many
pieces of metadata (e.g., title, description, creators, etc) in
attributes named like their RegTAP counterparts (see the class
documentation).  A few attributes deserve a second look.

First, ``service`` will, for resources that only have a single
capability, return a DAL service object ready for querying using the
respective protocol.  You should only use that attribute when the
original reqistry query constrained the service type, because otherwise
there is no telling what kind of service you will get back.

When the registry query did not constrain the service type, you can use
the ``access_modes`` method to see what capabilities are available.  For
instance::

  >>> res = registry.search(ivoid="ivo://org.gavo.dc/flashheros/q/ssa")[0]
  >>> res.access_modes()
  {'ssa', 'datalink#links-1.0', 'tap#aux', 'web', 'soda#sync-1.0'}

– this service can be accessed through SSA, TAP, a web interface, and
two special capabilities that pyvo cannot produce services for (mainly
because standalone service objects do not make much sense for them).

To obtain a service for one of the access modes pyVO does support, use
``get_service(mode)``.  For ``web``, this returns an object that opens a
web browser window when its ``query`` method is called.

RegistryResource-s also have a ``get_contact`` method.  Use this if the
service is down or seems to have bugs; you should in general get at
least an e-Mail address::

  >>> res.get_contact()
  'GAVO Data Center Team (++49 6221 54 1837) <gavo@ari.uni-heidelberg.de>'

Finally, the registry has an idea of what kind of tables are published
through a resource, much like the VOSI tables endpoint (as a matter of
fact, the Registry should contain exactly what is there, as VOSI tables
in effect just gives a part of the registry record).  Not all publishers
properly provide table metadata to the Registry, though, but most do these days,
and then you can run::

  >>> res.get_tables()
  {'ivoa.obscore': <Table name="ivoa.obscore">... 0 columns ...</Table>, 'flashheros.data': <Table name="flashheros.data">... 29 columns ...</Table>}


Reference/API
=============

.. automodapi:: pyvo.registry
.. automodapi:: pyvo.registry.regtap
.. automodapi:: pyvo.registry.rtcons
