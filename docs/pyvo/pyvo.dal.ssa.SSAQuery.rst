

SSAQuery
=====================

.. currentmodule:: pyvo.dal.ssa

.. autoclass:: SSAQuery
   :show-inheritance:

   .. rubric:: Attributes Summary

   Search Constraint Attributes:

   .. autosummary::
   
      ~SSAQuery.band
      ~SSAQuery.dec
      ~SSAQuery.format
      ~SSAQuery.pos
      ~SSAQuery.ra
      ~SSAQuery.size
      ~SSAQuery.time

   Other Attributes:

   ====================================================  ==========================================================
   :py:attr:`~pyvo.dal.query.DALQuery.baseurl`           the base URL of the service where the query will be 
                                                         submitted
   ----------------------------------------------------  ----------------------------------------------------------
   :py:attr:`~pyvo.dal.ssa.SSAQuery.std_parameters`      the list of predefined parameters supported by the SSA 
                                                         standard (read-only)
   ----------------------------------------------------  ----------------------------------------------------------
   :py:attr:`~pyvo.dal.query.DALQuery.protocol`          the type of protocol supported by this query instance
                                                         (read-only; set to 'ssa').  
   ----------------------------------------------------  ----------------------------------------------------------
   :py:attr:`~pyvo.dal.query.DALQuery.version`           the version of the protocol standard supported by this 
                                                         query instance (read-only)
   ====================================================  ==========================================================

   .. rubric:: Methods Summary

   .. autosummary::
   
      ~SSAQuery.execute

   .. rubric:: Methods Inherited from DALQuery

   .. autosummary::
   
      ~pyvo.dal.query.DALQuery.execute_stream
      ~pyvo.dal.query.DALQuery.execute_raw
      ~pyvo.dal.query.DALQuery.execute_votable
      ~pyvo.dal.query.DALQuery.getqueryurl
      ~pyvo.dal.query.DALQuery.getparam
      ~pyvo.dal.query.DALQuery.paramnames
      ~pyvo.dal.query.DALQuery.setparam
      ~pyvo.dal.query.DALQuery.unsetparam

   .. rubric:: Attributes Documentation
   
   .. autoattribute:: band
   .. autoattribute:: dec
   .. autoattribute:: format
   .. autoattribute:: pos
   .. autoattribute:: ra
   .. autoattribute:: size
   .. autoattribute:: time

   .. py:attribute:: std_parameters

      the list of predefined parameters supported by the SSA standard
      (read-only).   These names can be used to set constraints 
      generically via the 
      :py:meth:`~pyvo.dal.query.DALQuery.setparam` 
      method.  

      This is set to the following names with the given types and meanings:

      ==============  ==================  ========================================
      Parameter Name  Value Type          Meaning
      ==============  ==================  ========================================
      REQUEST         str                 query operation name (defaults to 
                                          "queryData")
      --------------  ------------------  ----------------------------------------
      VERSION         str                 the version of the protocol being used
                                          ("1.0" is assumed by the service when 
                                          not provided)
      --------------  ------------------  ----------------------------------------
      POS             2 floats delimited  Same as :py:attr:`pos` 
      --------------  ------------------  ----------------------------------------
      SIZE            float               Same as :py:attr:`size` 
      --------------  ------------------  ----------------------------------------
      BAND            str                 Same as :py:attr:`band` 
      --------------  ------------------  ----------------------------------------
      TIME            str                 Same as :py:attr:`time`
      --------------  ------------------  ----------------------------------------
      FORMAT          str                 Same as :py:attr:`format`
      --------------  ------------------  ----------------------------------------
      APERTURE
      --------------  ------------------  ----------------------------------------
      SPECRP
      --------------  ------------------  ----------------------------------------
      SPATRES
      --------------  ------------------  ----------------------------------------
      TIMERES
      --------------  ------------------  ----------------------------------------
      SNR
      --------------  ------------------  ----------------------------------------
      REDSHIFT
      --------------  ------------------  ----------------------------------------
      VARAMPL
      --------------  ------------------  ----------------------------------------
      TARGETNAME      str
      --------------  ------------------  ----------------------------------------
      TARGETCLASS     str
      --------------  ------------------  ----------------------------------------
      FLUXCALIB
      --------------  ------------------  ----------------------------------------
      WAVECALIB
      --------------  ------------------  ----------------------------------------
      PUBID           str                 the identifier for a specific publisher
                                          of the data; this can be used to 
                                          restrict results to those from a 
                                          specific archive.
      --------------  ------------------  ----------------------------------------
      CREATORID
      --------------  ------------------  ----------------------------------------
      COLLECTION
      --------------  ------------------  ----------------------------------------
      TOP
      --------------  ------------------  ----------------------------------------
      MAXREC
      --------------  ------------------  ----------------------------------------
      MTIME
      --------------  ------------------  ----------------------------------------
      COMPRESS
      --------------  ------------------  ----------------------------------------
      RUNID
      ==============  ==================  ========================================

   .. rubric:: Methods Documentation
   
   .. note:: See also the parent class, :py:class:`~pyvo.dal.query.DALQuery`, for
             descriptions of the inherited methods.  

   .. automethod:: execute

   
   
