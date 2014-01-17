

SIAQuery
=====================

.. currentmodule:: pyvo.dal.sia

.. autoclass:: SIAQuery
   :show-inheritance:

   .. rubric:: Attributes Summary

   Search Constraint Attributes:

   .. autosummary::
   
      ~SIAQuery.dec
      ~SIAQuery.format
      ~SIAQuery.intersect
      ~SIAQuery.pos
      ~SIAQuery.ra
      ~SIAQuery.size
      ~SIAQuery.verbosity

   Other Attributes:

   ====================================================  ==========================================================
   :py:attr:`~pyvo.dal.query.DALQuery.baseurl`           the base URL of the service where the query will be 
                                                         submitted
   ----------------------------------------------------  ----------------------------------------------------------
   :py:attr:`~pyvo.dal.sia.SIAQuery.std_parameters`      the list of predefined parameters supported by the SIA 
                                                         standard (read-only)
   ----------------------------------------------------  ----------------------------------------------------------
   :py:attr:`~pyvo.dal.sia.SIAQuery.allowed_intersects`  the four allowed values for the :py:attr:`~intersect` 
                                                         attribute (read-only)
   ----------------------------------------------------  ----------------------------------------------------------
   :py:attr:`~pyvo.dal.query.DALQuery.protocol`          the type of protocol supported by this query instance
                                                         (read-only; set to 'sia').  
   ----------------------------------------------------  ----------------------------------------------------------
   :py:attr:`~pyvo.dal.query.DALQuery.version`           the version of the protocol standard supported by this 
                                                         query instance (read-only)
   ====================================================  ==========================================================

   .. rubric:: Methods Summary

   .. autosummary::
   
      ~SIAQuery.execute

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
   
   .. py:attribute::  allowed_intersects

      the four allowed values to the :py:attr:`~intersect` attribute: 
      [ "COVERS",  "ENCLOSED",  "CENTER",  "OVERLAPS" ].  

   .. autoattribute:: dec
   .. autoattribute:: format
   .. autoattribute:: intersect
   .. autoattribute:: pos
   .. autoattribute:: ra
   .. autoattribute:: size
   .. py:attribute:: std_parameters

      the list of predefined parameters supported by the SIA standard
      (read-only).   These names can be used to set constraints 
      generically via the 
      :py:meth:`~pyvo.dal.query.DALQuery.setparam` 
      method.  

      This is set to the following names with the given types and meanings:

      ==============  ==================  ========================================
      Parameter Name  Value Type          Meaning
      ==============  ==================  ========================================
      POS             2 floats delimited  Same as :py:attr:`pos` 
      --------------  ------------------  ----------------------------------------
      SIZE            1 or 2 floats       Same as :py:attr:`size` 
                      delimited by a      
                      comma               
      --------------  ------------------  ----------------------------------------
      INTERSECT       str                 Same as :py:attr:`intersect` 
      --------------  ------------------  ----------------------------------------
      FORMAT          str                 Same as :py:attr:`format` 
      --------------  ------------------  ----------------------------------------
      VERB            int                 Same as :py:attr:`verbosity` 
      --------------  ------------------  ----------------------------------------
      NAXIS           1 or 2 ints         For services that generate images on the 
                      delimited by a      fly and support this parameter, create
                      comma               images with the given width and height 
                                          in pixels.
      --------------  ------------------  ----------------------------------------
      CFRAME          str; one of ICRS,   For services that generate images on the 
                      FK4, FK5, ECL,      fly and support this parameter, create
                      GAL, SGAL           images with the given coordinate frame.
      --------------  ------------------  ----------------------------------------
      EQUINOX         float               For services that generate images on the 
                                          fly and support this parameter, apply
                                          the given equinox (ignored if CFRAME is 
                                          ICRS).
      --------------  ------------------  ----------------------------------------
      PROJ            str                 For services that generate images on the 
                                          fly and support this parameter, apply
                                          the coordinate project given by the FITS
                                          3-character code (e.g. "SIN", "TAN", 
                                          etc.)
      --------------  ------------------  ----------------------------------------
      CRPIX           2 ints delimited    For services that generate images on the
                      by a comma          fly and support this parameter, create
                                          images with the given reference pixel.
      --------------  ------------------  ----------------------------------------
      CRVAL           2 floats delimited  For services that generate images on the
                      by a comma          fly and support this parameter, create
                                          images with the given reference position
                                          in decimal degrees in the requested 
                                          frame.
      --------------  ------------------  ----------------------------------------
      CDELT           2 floats delimited  For services that generate images on the
                      by a comma          fly and support this parameter, create
                                          images with the given pixel size along
                                          the width and height directions in 
                                          decimal degrees in the requested frame.
      --------------  ------------------  ----------------------------------------
      ROTANG          float               For services that generate images on the
                                          fly and support this parameter, create
                                          images with a coordinate system rotated
                                          by the given angle.  
      ==============  ==================  ========================================
      
   .. autoattribute:: verbosity
   

   .. rubric:: Methods Documentation
   
   .. note:: See also the parent class, :py:class:`~pyvo.dal.query.DALQuery`, for
             descriptions of the inherited methods.  

   .. automethod:: execute

   
