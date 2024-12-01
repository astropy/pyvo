.. _pyvo-discover:

******************************************
Global Dataset Discovery (`pyvo.discover`)
******************************************

One of the promises of the Virtual Observatory has always been that
researchers can globally look for data sets (spectra, say).  In the
early days of the VO, this looked relatively simple: Just enumerate all
image (in those days: SIAP) services, send the same query to them, and
then somehow shoehorn together their responses.

In reality, there are all kinds of small traps ranging from hanging
services to the sheer number of data collections. Hitting hundreds of
internet sites takes quite a bit of time even when everything works.  In
the meantime, the picture is further complicated by the emergence of
additional protocols.  Images, for instance, can be published through
SIA version 1, SIA version 2, and ObsTAP in 2024 – and in particular any
combination of that.

To keep global discovery viable, several techniques can be applied:

* pre-select the services by using the service footprints in space,
  time, and spectrum.
* elide services serving the same data collections
* filter duplicate responses before presenting them to the user.

This is the topic of this sub-module.

In early 2024, this is still in early development.


Basic Usage
===========

The basic API for dataset discovery is through functions accepting
constraints on

* space (currently, a cone, i.e., RA, Dec and a radius in degrees),
* spectrum (currently, a point in the spectrum as a spectral quantity),
  and
* time (an astropy.time.Time instance or a pair of them to denote an
  interval).

For instance::

  from pyvo import discover
  from astropy import units as u
  from astropy import time

  datasets, log = discover.images_globally(
    space=(273.5, -12.1, 0.1),
    spectrum=1*u.nm,
    time=(time.Time('1995-01-01'), time.Time('1995-12-31')))
  print(datasets)

The function returns a pair of lists.  ``datasets`` is a list of
`~pyvo.discover.ImageFound` instances.  This is the (potentially
long) list of datasets located.

The second returned value, ``log``, is a sequence of strings noting
which services failed and which returned how many records.  In
exploratory work, it is probably all right to discard the information,
but for research purposes, these log lines are an important part of the
provenance and must be retained – after all, you might have missed an
important clue just because a service was down at the moment you ran
your discovery; also, you might want to re-query the failing services at
some later stage.

All constraints are optional, but without a space constraint, no SIA1
services will be queried.  With spectrum and time constraints, it is
probably wise to pass ``inclusive=True`` for the time being, as far too
many resources do not define their coverage.

The discovery function accepts a few other parameters you should know
about.  These are discussed in the following sections.


``inclusive`` Searching
-----------------------

Unfortunately, many resources in the VO do not yet declare their
coverage.  In its default configuration, pyVO discovery will not query
services that do not explicitly say they cover the region of interest
and hence always skip these services (unless you manually pass them in,
see below).  To change that behaviour and try services that do not state
their coverage, pass ``inclusive=True``.  At this time, this will
usually dramatically increase the search time.

Setting ``inclusive`` to True will also include datasets that do not
declare their temporal of spectral coverage when coming for version 1
SIAP services [TODO: do that in obscore, too?].  This may
dramatically increase the number of false positives.  It is probably
wise to only try ``inclusive=True`` when desperate or when there is a
particular necessity to not miss any potentially applicable data.


The Watcher
-----------

Global discovery usually hits dozens of web services.  To see what is
going on, you can pass in a function accepting a single string as
``watcher``.  The trivial implementation would be::

  import datetime

  def watch(disco, msg):
    print(datetime.datetime.now(), msg)

  found, log = discover.images_globally(
    space=(3, 1, 0.2), watcher=watch)

Here, ``disco`` is an ``ImageDiscoverer`` instance; this way, you can
further inspect the state of things, e.g., by looking at the
``already_queried`` and ``failed_services`` attributes containing the
number of total services tried and of services that gave errors,
respectively.  Also, although that clearly goes beyond watching, you can
call the ``reset_services()`` method.  This empties the query queues and
thus in effect stops the discovery process.

Setting Timeouts
----------------

There are always some services that are broken.  A particularly
insidious sort of brokenness occurs when data centres run reverse
proxies (many do these days) that are up and try to connect to a backend
server intended to run the actual service.  In certain configurations,
it might take the reverse proxy literally forever to notice when a
backend server is unreachable, and meanwhile your global discovery will
hang, too.

Therefore, pyVO global discovery will give up after ``timeout`` seconds,
defaulting to 20 seconds.  Note that large data collections *may* take
longer than that to produce their response; but given the simple
constraints we support so far, we would probably consider them broken in
that case.  Reducing the timeout to just a few seconds will make pyVO
continue earlier on broken services.  But that of course increases the
risk of cutting off working services.

If in doubt, have a brief look at the log lines; if a service that
sounds promising shows a timeout, perhaps try again with a longer
timeout or use partial matching.


Overriding service selection
----------------------------

You can also pass a `pyvo.registry.RegistryResults` instance to
``services`` to override the automatic selection of services to query.
See the discussion of overriding the service selection in Discoverers_.


Discoverers
===========

For finer control of the discovery process, you can directly use
the `pyvo.discover.image.ImageDiscoverer` class.  It is constructed with
essentially the same parameters as the search function.

To run the discovery, first establish which services to query.  There
are two ways to do that:

* Call the ``discover_services()`` method.  This is what the search
  function does; it uses your constraints as above.
* Pass a `pyvo.registry.RegistryResults` instance to ``set_services``.
  This lets you do your own searches.  The image discoverer will only
  use resources that it knows how to handle.  For instance, it is safe
  to call something like::

    discoverer.set_services(
      registry.search(registry.Author("Hubble, %")))

  to query services that give a particular author.  More realistically,

  ::

    discoverer.set_services(
      registry.search(registry.Datamodel("obscore")))

  will restrict the operation to obscore services.

``set_services`` will purge redundant services, which means that
services that say they (or their data) is served by another service that
will already be queried will not be queried.  Outside of debugging, this
is what you want, but if you really do not want this, you can pass
``purge_redundant=False``.  Note, however, that you will still get only
one match per access URL of the dataset.

Once you have set the services, call ``query_services()`` to fill the
``results`` and ``log_messages`` attributes.  It may be informative to
watch these change from, say, a different thread.  Changing their
content has undefined results.

A working example would look like this::

  from pyvo import discover, registry
  from astropy.time import Time

  im_discoverer = discover.image.ImageDiscoverer(
    space=(274.6880, -13.7920, 0.1),
    time=(Time('1996-10-04'), Time('1996-10-10')))
  im_discoverer.set_services(
    registry.search(keywords=["heasarc rass"]))
  im_discoverer.query_services()
  print(im_discoverer.log_messages)
  print(im_discoverer.results)



Reference/API
=============

.. automodapi:: pyvo.discover
