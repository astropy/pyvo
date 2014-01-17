

SLAQuery
=====================

.. currentmodule:: pyvo.dal.sla

.. autoclass:: SLAQuery
   :show-inheritance:

   .. rubric:: Attributes Summary

   Search Constraint Attributes:

   .. autosummary::
   
      ~SLAQuery.wavelength
      ~SLAQuery.format

   Other Attributes:

   ====================================================  ==========================================================
   :py:attr:`~pyvo.dal.query.DALQuery.baseurl`           the base URL of the service where the query will be 
                                                         submitted
   ----------------------------------------------------  ----------------------------------------------------------
   :py:attr:`~pyvo.dal.sla.SLAQuery.std_parameters`      the list of predefined parameters supported by the SLA 
                                                         standard (read-only)
   ----------------------------------------------------  ----------------------------------------------------------
   :py:attr:`~pyvo.dal.query.DALQuery.protocol`          the type of protocol supported by this query instance
                                                         (read-only; set to 'sla').  
   ----------------------------------------------------  ----------------------------------------------------------
   :py:attr:`~pyvo.dal.query.DALQuery.version`           the version of the protocol standard supported by this 
                                                         query instance (read-only)
   ====================================================  ==========================================================
   
   .. rubric:: Methods Summary

   .. autosummary::
   
      ~SLAQuery.execute

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

   
   .. autoattribute:: format
   .. autoattribute:: wavelength

   .. py:attribute:: std_parameters

      the list of predefined parameters supported by the Cone Search 
      (SCS) standard (read-only).   These names can be used to set 
      constraints generically via the 
      :py:meth:`~pyvo.dal.query.DALQuery.setparam` 
      method.  

      This is set to the following names with the given types and meanings:

      ====================  ==================  ========================================
      Parameter Name        Value Type          Meaning
      ====================  ==================  ========================================
      REQUEST               str                 query operation name (defaults to 
                                                "queryData")
      --------------------  ------------------  ----------------------------------------
      VERSION               str                 the version of the protocol being used
                                                ("1.0" is assumed by the service when 
                                                not provided)
      --------------------  ------------------  ----------------------------------------
      WAVELENGTH            str                 Same as :py:attr:`wavelength`
      --------------------  ------------------  ----------------------------------------
      FORMAT                str                 Same as :py:attr:`format`
      --------------------  ------------------  ----------------------------------------
      CHEMICAL_ELEMENT      str
      --------------------  ------------------  ----------------------------------------
      INITIAL_LEVEL_ENERGY  str                 a range list for constraining the 
                                                transitions' upper energy levels
      --------------------  ------------------  ----------------------------------------
      FINAL_LEVEL_ENERGY    str                 a range list for constraining the 
                                                transitions' lower energy levels
      --------------------  ------------------  ----------------------------------------
      TEMPERATURE           
      --------------------  ------------------  ----------------------------------------
      EINSTEIN_A            
      --------------------  ------------------  ----------------------------------------
      PROCESS_TYPE          
      --------------------  ------------------  ----------------------------------------
      PROCESS_NAME          
      ====================  ==================  ========================================
   
   .. rubric:: Methods Documentation
   
   .. note:: See also the parent class, :py:class:`~pyvo.dal.query.DALQuery`, for
             descriptions of the inherited methods.  

   .. automethod:: execute

   
   
