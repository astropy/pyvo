
================
The pyvo Package
================

.. py:module:: pyvo

PyVO is a package providing access to remote data and services of the 
Virtual observatory (VO) using Python.  

The pyvo module currently provides these main capabilities:

* find archives that provide particular data of a particular type and/or 
  relates to a particular topic

  *  :py:func:`~pyvo.regsearch`

* search an archive for datasets of a particular type

  *  :py:func:`~pyvo.imagesearch`, :py:func:`~pyvo.spectrumsearch`

* do simple searches on catalogs or databases

  *  :py:func:`~pyvo.conesearch`, :py:func:`~pyvo.linesearch`, :py:func:`~pyvo.tablesearch`

Submodules provide additional functions and classes for greater control over
access to these services.

This module also exposes the exception classes raised by the above functions, 
of which DALAccessError is the root parent exception. 


###########
API Summary
###########

*********
Functions
*********

=============================== ================================================================
:py:func:`~pyvo.conesearch`     equivalent to :py:func:`pyvo.dal.scs.search`
:py:func:`~pyvo.imagesearch`    equivalent to :py:func:`pyvo.dal.sia.search`
:py:func:`~pyvo.spectrumsearch` equivalent to :py:func:`pyvo.dal.ssa.search`
:py:func:`~pyvo.linesearch`     equivalent to :py:func:`pyvo.dal.sla.search`
:py:func:`~pyvo.tablesearch`    equivalent to :py:func:`pyvo.dal.tap.search`
:py:func:`~pyvo.regsearch`      equivalent to :py:func:`pyvo.registry.regtap.search`
=============================== ================================================================

**********
Exceptions
**********

.. 
   .. currentmodule:: pyvo.dal.query

   .. autosummary:: 

      DALAccessError
      DALProtocolError
      DALFormatError
      DALServiceError
      DALQueryError

   .. currentmodule:: pyvo

============================================  ==================================
:py:class:`~pyvo.dal.query.DALAccessError`    a base class for all failures while accessing a DAL service
:py:class:`~pyvo.dal.query.DALProtocolError`  a base exception indicating that a DAL service responded in an erroneous way.  
:py:class:`~pyvo.dal.query.DALFormatError`    an exception indicating that a DAL response contains fatal format errors.
:py:class:`~pyvo.dal.query.DALServiceError`   an exception indicating a failure communicating with a DAL service.
:py:class:`~pyvo.dal.query.DALQueryError`     an exception indicating an error by a working DAL service while processing a query.  
============================================  ==================================

###########
API Details
###########

*********
Functions
*********

.. py:function:: regsearch([keywords=None, servicetype=None, waveband=None])

   equivalent to :py:func:`pyvo.registry.regtap.search`

.. py:function:: conesearch(url[, radius=1.0, verbosity=2])

   equivalent to :py:func:`pyvo.dal.scs.search`

.. py:function:: imagesearch(url, pos, size[, format='all', intersect='overlaps', verbosity=2])

   equivalent to :py:func:`pyvo.dal.sia.search`

.. py:function:: spectrumsearch(url, pos, size[, format='all'])

   equivalent to :py:func:`pyvo.dal.ssa.search`

.. py:function:: linesearch(url, wavelength)

   equivalent to :py:func:`pyvo.dal.sla.search`

.. py:function:: tablesearch(url, query[, language="ADQL", maxrec=None, uploads=None])

   equivalent to :py:func:`pyvo.dal.tap.search`

