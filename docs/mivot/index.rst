********************
MIVOT (`pyvo.mivot`)
********************
This module contains the new feature of annotations in VOTable.
Astropy version >= 6.0 is required.

Introduction
============
.. pull-quote::

    Model Instances in VOTables (MIVOT) defines a syntax to map VOTable
    data to any model serizalized in VO-DML. The annotation operates as a
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

    -- `Model Instances in VOTables <https://ivoa.net/documents/MIVOT/20230620/REC-mivot-1.0.pdf>`_


Usage
-----
The API allows you to obtain a model view on the last read data row, this usage corresponds to the layer 3 described below.

.. doctest-remote-data::
    >>> import pyvo
    >>> import os
    >>> from astropy.utils.data import get_pkg_data_filename
    >>> from pyvo.mivot.viewer.model_viewer import ModelViewer
    >>> from pyvo.mivot.version_checker import check_astropy_version
    >>> from pyvo.utils.prototype import activate_features
    >>> activate_features('MIVOT')
    >>> votable = get_pkg_data_filename("data/simple-annotation-votable.xml", package="pyvo.mivot.tests")
    >>> if check_astropy_version(): # doctest: +SKIP
    ...     m_viewer = ModelViewer(votable)
    ...     row_view = m_viewer.get_next_row_view()
    ...     print(row_view.longitude.value)
    ...     print(row_view.Coordinate_coosys.PhysicalCoordSys_frame.spaceRefFrame.value)
        10.0
        ICRS


The model view is a dynamically generated Python object whose field names are derived from
the dmroles of the MIVOT elements. There is no checking against the model structure at this level.

Example for epoch propagation
-----------------------------
.. doctest-remote-data::
    >>> if check_astropy_version():
    ...     with ModelViewer(votable) as m_viewer: # doctest: +SKIP
    ...         row_view = m_viewer.get_next_row_view()
    ...         past_ra, past_dec = row_view.apply_space_motion(dt=-42 * u.year)
    ...         future_ra, future_dec = row_view.apply_space_motion(dt=2 * u.year)
    ...         print("past_ra, past_dec :", row_view.apply_space_motion(dt=-42 * u.year))
    ...         print("future_ra, future_dec :", row_view.apply_space_motion(dt=2 * u.year))
    past_ra, past_dec : (<Longitude 9.9998763 deg>, <Latitude 10.00024364 deg>)
    future_ra, future_dec : (<Longitude 10.00000563 deg>, <Latitude 9.99998891 deg>)

Implementation
==============
The implementation relies on the Astropy's write and read annotation modules (PR#15390),
which allows to get and set Mivot blocks from/into VOTables.
We use this new Astropy feature, MIVOT, to retrieve the MIVOT block.

This implementation is built in 3 layers, denoting the abstraction level in relation to the XML block.

Layer 0: ModelViewer
--------------------
Provide the MIVOT block as it is in the VOTable: No references are resolved.
The Mivot block is provided as an xml tree.

Layer 1: ModelViewerLayer1
--------------------------
Provide access to an xml tree whose structure matches the model view of the current row.
The internal references have been resolved. The attribute values have been set with the actual data values.
This XML element is intended to be used as a basis for building any objects.
The layer 1 output can be browsed using XPATH queries.

Layer 2: ModelViewerLayer2
--------------------------
Just a few methods to make the browsing of the layer 1 output easier.
The layer 2 API allows users to retrieve MIVOT elements by their @dmrole or @dmtype.
At this level, the MIVOT block must still be handled as an xml element.
This module is not completely implemented.

Layer 3: ModelViewerLayer3
--------------------------
ModelViewerLayer3 generates, from the layer 1 output, a nested dictionary
representing the entire XML INSTANCE with its hierarchy.
From this dictionary, we build a :py:class:`pyvo.mivot.viewer.mivot_class.MivotClass`,
which is a dictionary containing only the essential information used to process data.
MivotClass basically stores all XML objects in its attribute dictionary :py:attr:`__dict__`.



Reference/API
=============

.. automodapi:: pyvo.mivot.viewer
.. automodapi:: pyvo.mivot.seekers
.. automodapi:: pyvo.mivot.features
.. automodapi:: pyvo.mivot.utils


