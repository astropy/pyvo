**********************
MIVOT (``pyvo.mivot``)
**********************

This module contains the new feature of handling model annotations in VOTable.
Astropy version >= 6.0 is required.

Introduction
============
.. pull-quote::

    Model Instances in VOTables (MIVOT) defines a syntax to map VOTable
    data to any model serialized in VO-DML. The annotation operates as a
    bridge between the data and the model. It associates the column/param
    metadata from the VOTable to the data model elements (class, attributes,
    types, etc.) [...].
    The data model elements are grouped in an independent annotation block
    complying with the MIVOT XML syntax. This annotation block is added
    as an extra resource element at the top of the VOTable result resource. The
    MIVOT syntax allows to describe a data structure as a hierarchy of classes.
    It is also able to represent relations and composition between them. It can
    also build up data model objects by aggregating instances from different
    tables of the VOTable.

- Model Instances in VOTables is a VO `standard <https://ivoa.net/documents/MIVOT/20230620/REC-mivot-1.0.pdf>`_
- Requires Astropy>=6.0
- ``pyvo.mivot`` is a prototype feature which must be activated with ``activate_features("MIVOT")``


Implementation Scope
====================
This implementation is totally model-agnostic.

- It does not operate any validation against specific data models.
- It just requires the annotation syntax being compliant with the standards.

However, many data samples used for the test suite and provided as examples
are based on the ``EpochPropagation`` class of the ``Mango`` data model
that is still a draft.
This class collects all the parameters we need to compute the epoch propagation of moving sky objects.
Some of the examples have been provided by a special end-point of the Vizier cone-search service
(https://vizier.cds.unistra.fr/viz-bin/conesearch/V1.5/) that maps query results to this model.

.. image:: _images/mangoEpochPosition.png
   :width: 500
   :alt: EpochPropagation class used to validate this api.

It is to be noted that the Vizier service does not annotate errors at the time of writing (Q1 2024)

The implementation uses the Astropy read/write annotation module (6.0+),
which allows to get (and set) Mivot blocks from/into VOTables as an XML element serialized as a string.

.. pull-quote::

    Not all MIVOT features are supported by this implementation, which mainly focuses on the
    epoch propagation use case:

    - ``JOIN`` features are not supported.
    - ``TEMPLATES`` with more than one ``INSTANCE`` not supported.


Using the MIVOT package
=======================

The ``pyvo.mivot`` module can be used to either read or build annotations.

.. toctree::
   :maxdepth: 2
   
   viewer
   annoter
   writer
   example
   annoter_tips
   