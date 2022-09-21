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
  one of tap, ssa, sia, conesearch (or full ivoids for other service
  types).  This is the constraint you want
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
  *RegTAP 1.2 Extension*
* :py:class:`pyvo.registry.Spectral` (``spectral``): match resources
  covering a certain part of the spectrum (usually, but not limited to,
  the electromagnetic spectrum).  *RegTAP 1.2 Extension*
* :py:class:`pyvo.registry.Temporal` (``temporal``): match resources
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

  >>> resources = registry.search(registry.Waveband("Radio", "Millimeter"))

is equivalent to:

.. doctest-remote-data::

  >>> resources = registry.search(waveband=["Radio", "Millimeter"])

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
you would say:

.. doctest-remote-data::

  >>> resources = registry.search(registry.UCD("src.redshift"),
  ...                             registry.Freetext("supernova"))

After that, ``resources`` is an instance of
:py:class:`pyvo.registry.RegistryResults`, which you can iterate over.  In
interactive data discovery, however, it is usually preferable to use the
``to_table`` method for an overview of the resources available:

.. doctest-remote-data::

  >>> resources.to_table()  # doctest: +IGNORE_OUTPUT
  <Table length=158>
                               title                              ...        interfaces
                               str67                              ...          str24
  --------------------------------------------------------------- ... ------------------------
                Asiago Supernova Catalogue (Barbon et al., 1999-) ... conesearch, tap#aux, web
                    Asiago Supernova Catalogue (Version 2008-Mar) ... conesearch, tap#aux, web
       Sloan Digital Sky Survey-II Supernova Survey (Sako+, 2018) ... conesearch, tap#aux, web
  ...


The idea is that in notebook-like interfaces you can pick resources by
title, description, and perhaps the access mode (“interface”) offered.
In the list of interfaces, you will sometimes spot an ``#aux`` after a
standard id; this is a minor VO technicality that you can in practice
ignore.  For instance, you can simply construct
:py:class:`pyvo.dal.TAPService`-s from ``tap#aux`` interfaces.

Once you have found a resource you would like to query, you can pick it
by index; however,
this will not be stable across multiple executions.
Hence, RegistryResults also supports referencing results by short name,
which is the style we recommend.  Using full ivoids is possible, too,
and safer because these are guaranteed to be unique (which short names
are not), but it is rather clunky, and in the real VO short name
collisions should be very rare.

Use the ``get_service`` method of
:py:class:`pyvo.registry.RegistryResource` to obtain a DAL service
object for a particular sort of interface.
To query the fourth match using simple cone search, you would
thus say:

.. doctest-remote-data::

  >>> resources["II/283"].get_service("conesearch").search(pos=(120, 73), sr=1)  # doctest: +IGNORE_OUTPUT
  <Table length=1>
    _RAJ2000     _DEJ2000      _r    recno ... NED    RAJ2000      DEJ2000
      deg          deg        deg          ...        "h:m:s"      "d:m:s"
    float64      float64    float64  int32 ... str3    str12        str12
  ------------ ------------ -------- ----- ... ---- ------------ ------------
  117.98645833  73.00961111 0.588592   986 ...  NED 07 51 56.750 +73 00 34.60

To operate TAP services, you need to know what tables make up a
resource; you could construct a TAP service and access its ``tables``
attribute, but you can take a shortcut and call a RegistryResource's
``get_tables`` method for a rather similar result:

.. doctest-remote-data::

  >>> tables = resources["II/283"].get_tables()  # doctest: +IGNORE_WARNINGS
  >>> list(tables.keys())
  ['II/283/sncat']
  >>> tables['II/283/sncat'].columns
  [<BaseParam name="n_x"/>, <BaseParam name="t"/>, <BaseParam name="recno"/>, <BaseParam name="n_sn"/>, <BaseParam name="sn"/>, <BaseParam name="u_sn"/>, <BaseParam name="galaxy"/>, <BaseParam name="rag"/>, <BaseParam name="deg"/>, <BaseParam name="mtype"/>, <BaseParam name="i"/>, <BaseParam name="pa"/>, <BaseParam name="hrv"/>, <BaseParam name="z"/>, <BaseParam name="u_z"/>, <BaseParam name="n_bmag"/>, <BaseParam name="bmag"/>, <BaseParam name="logd25"/>, <BaseParam name="x"/>, <BaseParam name="y"/>, <BaseParam name="u_y"/>, <BaseParam name="n_y"/>, <BaseParam name="band"/>, <BaseParam name="maxmag"/>, <BaseParam name="u_maxmag"/>, <BaseParam name="type"/>, <BaseParam name="epmax"/>, <BaseParam name="u_epmax"/>, <BaseParam name="disc"/>, <BaseParam name="simbad"/>, <BaseParam name="ned"/>, <BaseParam name="raj2000"/>, <BaseParam name="dej2000"/>]

In this case, this is a table with one of VizieR's somewhat funky names.
To run a TAP query based on this metadata, do something like:

.. doctest-remote-data::

  >>> resources["II/283"].get_service("tap#aux").run_sync(
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
with the query facility (this uses python's webbrowser module):

.. doctest-skip::

  >>> resources["II/283"].get_service("web").search()  # doctest: +IGNORE_OUTPUT

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
instance.  The opening example could be written like this:

.. This one is too expensive to run as part of CI/testing
.. doctest-skip::

  >>> from astropy.coordinates import SkyCoord
  >>> my_obj = SkyCoord.from_name("Bellatrix")
  >>> for res in registry.search(waveband="infrared", servicetype="spectrum"):
  ...     print(res.service.search(pos=my_obj, size=0.001))
  ...

In reality, you will have to add some error handling to this kind of
all-VO queries: in a wide and distributed network, some service is
always down.  See `Appendix: Robust All-VO Queries`_

The central point is: With a servicetype constraint, each result has
a well-defined ``service`` attribute that contains some subclass of
dal.Service and that can be queried in a uniform fashion.

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
instance:

.. doctest-remote-data::

  >>> res = registry.search(ivoid="ivo://org.gavo.dc/flashheros/q/ssa")[0]
  >>> res.access_modes()  # doctest: +IGNORE_OUTPUT
  {'ssa', 'datalink#links-1.0', 'tap#aux', 'web', 'soda#sync-1.0'}

– this service can be accessed through SSA, TAP, a web interface, and
two special capabilities that pyvo cannot produce services for (mainly
because standalone service objects do not make much sense for them).

To obtain a service for one of the access modes pyVO does support, use
``get_service(mode)``.  For ``web``, this returns an object that opens a
web browser window when its ``query`` method is called.

RegistryResource-s also have a ``get_contact`` method.  Use this if the
service is down or seems to have bugs; you should in general get at
least an e-Mail address:

.. doctest-remote-data::

  >>> res.get_contact()
  'GAVO Data Center Team (++49 6221 54 1837) <gavo@ari.uni-heidelberg.de>'

Finally, the registry has an idea of what kind of tables are published
through a resource, much like the VOSI tables endpoint (as a matter of
fact, the Registry should contain exactly what is there, as VOSI tables
in effect just gives a part of the registry record).  Not all publishers
properly provide table metadata to the Registry, though, but most do these days,
and then you can run:

.. doctest-remote-data::

  >>> res.get_tables()  # doctest: +IGNORE_OUTPUT
  {'flashheros.data': <Table name="flashheros.data">... 29 columns ...</Table>, 'ivoa.obscore': <Table name="ivoa.obscore">... 0 columns ...</Table>}


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
run all-VO queries without reading at least this sentence)::

    from astropy import table
    from pyvo import registry

    QUERY = "SELECT TOP 1 dataproduct_type from ivoa.obscore"

    results = []
    for svc_rec in registry.search(
              datamodel="obscore", servicetype="tap"):
          print("Querying {}".format(svc_rec.res_title))
          try:
              svc = svc_rec.get_service("tap")
              results.append(
                  svc.run_sync(QUERY).to_table())
          except KeyboardInterrupt:
              # someone lost their patience with a service.  Query next.
              pass
          except Exception as msg:
              # some service is broken; you *should* complain, but
              print("  Broken: {} ({}).  Complain to {}.\n".format(
                  svc_rec.ivoid, msg, svc_rec.get_contact()))
          break

    total_result = table.vstack(results)
    print(total_result)
