

SIARecord
======================

.. currentmodule:: pyvo.dal.sia

.. autoclass:: SIARecord
   :show-inheritance:

   .. rubric:: Attributes Summary

   .. autosummary::
   
      ~SIARecord.acref
      ~SIARecord.dateobs
      ~SIARecord.dec
      ~SIARecord.format
      ~SIARecord.instr
      ~SIARecord.naxes
      ~SIARecord.naxis
      ~SIARecord.ra
      ~SIARecord.title

   .. rubric:: Methods Summary

   .. autosummary::
   
      ~pyvo.dal.query.Record.cachedataset
      ~pyvo.dal.query.Record.fielddesc
      ~pyvo.dal.query.Record.get
      ~pyvo.dal.query.Record.getdataset
      ~SIARecord.getdataurl
      ~pyvo.dal.query.Record.make_dataset_filename
      ~SIARecord.suggest_dataset_basename
      ~SIARecord.suggest_extension
   
   
   In addition, ``SIARecord`` supports the usual functions associated
   with dictionaries:  ``get(key[, default])``, ``has_key(key)``,
   ``items()``, ``iteritems()``, ``iterkeys()``, ``itervalues()``,
   ``keys()``, ``values()``. 
   

   .. rubric:: Attributes Documentation

   
   .. autoattribute:: acref
   .. autoattribute:: dateobs
   .. autoattribute:: dec
   .. autoattribute:: format
   .. autoattribute:: instr
   .. autoattribute:: naxes
   .. autoattribute:: naxis
   .. autoattribute:: ra
   .. autoattribute:: title

   .. rubric:: Methods Documentation
   
   .. note:: See also the parent class, :py:class:`~pyvo.dal.query.Record`, for
             descriptions of the inherited methods.  

   .. automethod:: getdataurl
   .. automethod:: suggest_dataset_basename
   .. automethod:: suggest_extension

   
   
