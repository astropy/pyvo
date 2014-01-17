
.. py:module:: pyvo.nameresolver

==================================
The pyvo.namesolver Package
==================================

.. note:: the Astropy package provides object-to-position resolution
          (see :ref:`resolve-names` for an example),
          so future versions of PyVO will migrate to use the Astropy
          implementation.  Thus, *the* :py:mod:`pyvo.nameresolver`
          *module will be deprecated*.  

          Direct support for Astropy coordinate types by the data
          access services is also planned for future versions of
          PyVO.  

          The support for the CDS Sesame Service within the 
          :py:mod:`pyvo.nameresolver.sesame` will be evolved
          appropriately for accessing other source information
          available from the service.  

The current default implementation available in the
**pyvo.nameresolver** module is that provided by the
:py:mod:`~pyvo.nameresolver.sesame` sub-module.  

.. automodapi:: pyvo.nameresolver.sesame




