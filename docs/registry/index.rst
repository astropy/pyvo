.. _pyvo-registry:

**************************
Registry (`pyvo.registry`)
**************************

This subpackage let you find data access services using search parameters.

Getting started
===============
Registry searches are performed using the :py:meth:`pyvo.registry.search`
method.

>>> from pyvo.registry import search as regsearch

It is possible to match against a list of ``keywords`` to find resources
related to a particular topic, for instances services containing data about
quasars.

>>> services = regsearch(keywords=['quasar'])

A single keyword can be specified as a single string instead of a list.

>>> services = regsearch(keywords='quasar')

Furthermore the search can be limited to a certain ``servicetype``, one of
sia, ssa, scs, sla, tap.

>>> services = regsearch(keywords=['quasar'], servicetype='tap')

Filtering by the desired waveband is also possible.

>>> services = regsearch(
...     keywords=['quasar'], servicetype='tap', waveband='x-ray')

And at last, the data model can be specified.

>>> obscore_services = regsearch(datamodel='ObsCore')

Search results
==============
Registry search results are similar to :ref:`pyvo-resultsets`.

See :py:class:`pyvo.registry.regtap.RegistryResource` for a listing of row
attributes.

Reference/API
=============

.. automodapi:: pyvo.registry
.. automodapi:: pyvo.registry.regtap
