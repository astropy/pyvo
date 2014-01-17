

SCSQuery
=====================

.. currentmodule:: pyvo.dal.scs

.. autoclass:: SCSQuery
   :show-inheritance:

   .. rubric:: Attributes Summary

   Search Constraint Attributes:

   .. autosummary::
   
      ~SCSQuery.dec
      ~SCSQuery.pos
      ~SCSQuery.ra
      ~SCSQuery.radius
      ~SCSQuery.sr
      ~SCSQuery.verbosity

   Other Attributes:

   ====================================================  ==========================================================
   :py:attr:`~pyvo.dal.query.DALQuery.baseurl`           the base URL of the service where the query will be 
                                                         submitted
   ----------------------------------------------------  ----------------------------------------------------------
   :py:attr:`~pyvo.dal.scs.SCSQuery.std_parameters`      the list of predefined parameters supported by the SCS 
                                                         standard (read-only)
   ----------------------------------------------------  ----------------------------------------------------------
   :py:attr:`~pyvo.dal.query.DALQuery.protocol`          the type of protocol supported by this query instance
                                                         (read-only; set to 'scs').  
   ----------------------------------------------------  ----------------------------------------------------------
   :py:attr:`~pyvo.dal.query.DALQuery.version`           the version of the protocol standard supported by this 
                                                         query instance (read-only)
   ====================================================  ==========================================================
   
   .. rubric:: Methods Summary

   .. autosummary::
   
      ~SCSQuery.execute
      ~SCSQuery.execute_votable
      ~SCSQuery.getqueryurl

   .. rubric:: Methods Inherited from DALQuery

   .. autosummary::
   
      ~pyvo.dal.query.DALQuery.execute_stream
      ~pyvo.dal.query.DALQuery.execute_raw
      ~pyvo.dal.query.DALQuery.getqueryurl
      ~pyvo.dal.query.DALQuery.getparam
      ~pyvo.dal.query.DALQuery.paramnames
      ~pyvo.dal.query.DALQuery.setparam
      ~pyvo.dal.query.DALQuery.unsetparam

   .. rubric:: Attributes Documentation

   .. autoattribute:: dec
   .. autoattribute:: pos
   .. autoattribute:: ra
   .. autoattribute:: radius
   .. autoattribute:: sr
   .. autoattribute:: verbosity
   .. py:attribute:: std_parameters

      the list of predefined parameters supported by the Cone Search 
      (SCS) standard (read-only).   These names can be used to set 
      constraints generically via the 
      :py:meth:`~pyvo.dal.query.DALQuery.setparam` 
      method.  

      This is set to the following names with the given types and meanings:

      ==============  ==================  ========================================
      Parameter Name  Value Type          Meaning
      ==============  ==================  ========================================
      RA              float               Same as :py:attr:`ra`
      --------------  ------------------  ----------------------------------------
      DEC             float               Same as :py:attr:`dec`
      --------------  ------------------  ----------------------------------------
      SR              float               Same as :py:attr:`radius`
      ==============  ==================  ========================================

   .. rubric:: Methods Documentation
   
   .. note:: See also the parent class, :py:class:`~pyvo.dal.query.DALQuery`, for
             descriptions of the inherited methods.  

   .. automethod:: execute
   .. automethod:: execute_votable
   .. automethod:: getqueryurl

   
   
