
.. py:module:: pyvo.dal

********************
The pyvo.dal Package
********************

The ``pyvo.dal`` module encapsulates the implementation of the DAL
services.  The :py:mod:`~pyvo.dal.query` sub-module provides DAL
behaviors through a set of base classes and common exception classes.
The implementations for the specific types of services are handle the
sub-modules :py:mod:`~pyvo.dal.scs`, :py:mod:`~pyvo.dal.sia`, 
:py:mod:`~pyvo.dal.ssa`, :py:mod:`~pyvo.dal.sla`

.. automodapi:: pyvo.dal.query
.. include:: scs.rst
.. include:: sia.rst
.. include:: ssa.rst
.. include:: sla.rst
.. include:: tap.rst
