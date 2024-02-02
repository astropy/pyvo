********************
MIVOT (`pyvo.mivot`)
********************
This module contains the new feature of annotations in VOTable.
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

    -- `Model Instances in VOTables <https://ivoa.net/documents/MIVOT/20230620/REC-mivot-1.0.pdf>`_


Usage
-----
The API allows you to obtain different levels of model views on the last read data row. These levels are described below.
The lowest levels are model agnostic.

They provide tools to browse model instances dynamically generated. The understanding of the model elements is the responsibility of the final user.

The highest level (4) is based on the MANGO draft model and especially to its.
It has been designed to solve the EpochPropagation use case risen at 2023 South Spring Interop.
The 3 lowest levels are totally model agnostic whereas the 4th  one is based on the `MANGO <https://github.com/ivoa-std/MANGO>`_
model proposal as it was at the time of writing.

The model view is a dynamically generated as Python data structures whose content is derived from
the ``dmroles`` of the MIVOT elements. There is no checking against the model structure at this level.

Implementation
==============
The implementation relies on the Astropy's write and read annotation modules (6.0+),
which allows to get and set Mivot blocks from/into VOTables as an XML element serialized in a string.
We use this new Astropy feature (PR #15390) to retrieve the MIVOT block.

This implementation is split in 4 levels, each representing a specific level of abstraction,
from the XML block to a ``SkyCOord`` instance.

Level 0: Astropy Resource
-------------------------
Provide the MIVOT block as it is in the VOTable: No references are resolved.
The string delivered by Astropy is converted into an XML complex element.
This feature is available in Astropy 6.0.

.. doctest-remote-data::
    >>> from xml.etree import ElementTree as etree
    >>> from astropy.io.votable import parse
    >>> from pyvo.mivot.utils.xml_utils import XmlUtils
    >>> resource = parse("votable.xml").resources[0] # doctest: +SKIP
    ... # extract a pretty string serialization of the mapping block
    ... # namespace is purged
    >>> str_mapping_block = (resource.mivot_block.content # doctest: +SKIP
    ...                      .replace("xmlns='http://www.ivoa.net/xml/mivot'", '')
    ...                      )
    >>> print(str_mapping_block) # doctest: +SKIP
    <VODML>
      <REPORT status="OK"> hand-made mapping </REPORT>
      ...
      <GLOBALS>
          ...
      </GLOBALS>
      <TEMPLATES>
        <INSTANCE dmtype="mango:EpochPosition">
          <ATTRIBUTE dmrole="mango:EpochPosition.longitude" dmtype="ivoa:RealQuantity" ref="pos_RA" unit="deg">
          </ATTRIBUTE>
             ...
          </INSTANCE>
      </TEMPLATES>
    </VODML>


Level 1: ModelViewerLevel1
--------------------------
Provide access to an xml tree whose structure matches the model view of the current row.
The internal references have been resolved. The attribute values have been set with the actual data values.
This XML element is intended to be used as a basis for building any objects.
The level 1 output can be browsed using XPATH queries.

.. doctest-remote-data::
    >>> from astropy.io.votable import parse
    >>> from xml.etree import ElementTree as etree
    >>> from pyvo.mivot.utils.xml_utils import XmlUtils
    >>> from pyvo.mivot.viewer.model_viewer_level1 import ModelViewerLevel1, ModelViewerLevel2
    >>> m_viewer = ModelViewerLevel1("votable.xml") # doctest: +SKIP
    >>> m_viewer.get_next_row() # doctest: +SKIP
    ... # return the XML element mapping the data row
    ... # internal references are resolved
    ... # attribute references have been replaced with table rows values
    >>> XmlUtils.pretty_print(m_viewer._get_model_view()) # doctest: +SKIP
    <TEMPLATES>
        <INSTANCE dmtype="mango:EpochPosition">
            <ATTRIBUTE dmrole="mango:EpochPosition.longitude" ... value="10.0"/>
            <ATTRIBUTE dmrole="mango:EpochPosition.latitude" ... value="10.0"/>
            ....

            <INSTANCE dmid="SpaceFrame_ICRS" dmtype="coords:SpaceSys" dmrole="coords:Coordinate.coosys">
                ...
               <ATTRIBUTE dmrole="coords:SpaceFrame.spaceRefFrame" dmtype="ivoa:string" value="ICRS"/>
            </INSTANCE>
         </INSTANCE>
    </TEMPLATES>


Level 2: ModelViewerLevel2
--------------------------
Just a few methods to make the browsing of the level 1 output easier.
The level 2 API allows users to retrieve MIVOT elements by their ``@dmrole`` or ``@dmtype``.
At this level, the MIVOT block must still be handled as an XML element.

.. doctest-remote-data::
    >>> from astropy.io.votable import parse
    >>> from pyvo.mivot.utils.xml_utils import XmlUtils
    >>> from pyvo.mivot.viewer.model_viewer_level1 import ModelViewerLevel1, ModelViewerLevel2
    >>> m_viewer = ModelViewerLevel1("votable.xml") # doctest: +SKIP
    >>> m_viewer.get_next_row() # doctest: +SKIP
    >>> m_viewer_level2 = ModelViewerLevel2(m_viewer) # doctest: +SKIP
    >>> XmlUtils.pretty_print(m_viewer_level2.get_instance_by_role("coords:PhysicalCoordSys.frame")) # doctest: +SKIP
    <INSTANCE dmrole="coords:PhysicalCoordSys.frame" dmtype="coords:SpaceFrame">
        <ATTRIBUTE dmrole="coords:SpaceFrame.spaceRefFrame" dmtype="ivoa:string" value="ICRS"/>
    </INSTANCE>

Level 3: ModelViewerLevel3
--------------------------
ModelViewerLevel3 generates, from the level 1 output, a nested dictionary
representing the entire XML INSTANCE with its hierarchy.
From this dictionary, we build a :py:class:`pyvo.mivot.viewer.mivot_class.MivotClass`,
which is a dictionary containing only the essential information used to process data.
MivotClass basically stores all XML objects in its attribute dictionary :py:attr:`__dict__`.
All properties can be retrieved as instance attributes.

.. doctest-remote-data::
    >>> row_view = m_viewer.get_next_row_view() # doctest: +SKIP
    >>> print(row_view.longitude.value) # doctest: +SKIP
    >>> print(row_view.Coordinate_coosys.PhysicalCoordSys_frame.spaceRefFrame.value) # doctest: +SKIP
    >>> print(row_view.sky_coordinate) # doctest: +SKIP
        5.0
        ICRS
        <SkyCoord (ICRS): (ra, dec, distance) in (deg, deg, pc)
            (5., -5., 125.)
         (pm_ra_cosdec, pm_dec, radial_velocity) in (mas / yr, mas / yr, km / s)
            (6., -6., 7.)>

Level 4: EpochPropagation Feature
---------------------------------
At this level, science ready objects are directly extracted from the annotation block. The model(s) is totally hidden.
The current implementation can build ``SkyCoord`` instances from a ``MANGO:EpochPosition`` XML blocks.
The ``apply_space_motion`` transformation has also been wrapped in.
This first science level implementation has been issued on request of the IVOA application working group (Tucson 2023)
for a convenient solution based on MIVOT for processing epoch propagation.

.. doctest-remote-data::
    >>> with ModelViewerLevel1(votable) as m_viewer: # doctest: +SKIP
    ...     row_view = m_viewer.get_next_row_view()
    ...     epoch_propagation = row_view.epoch_propagation
    ...     past_ra, past_dec = epoch_propagation.apply_space_motion(dt=-42 * u.year)
    ...     future_ra, future_dec = epoch_propagation.apply_space_motion(dt=2 * u.year)
    ...     print("past_ra, past_dec :", epoch_propagation.apply_space_motion(dt=-42 * u.year))
    ...     print("future_ra, future_dec :", epoch_propagation.apply_space_motion(dt=2 * u.year))
    past_ra, past_dec : (<Longitude 4.9998763 deg>, <Latitude -5.00024364 deg>)
    future_ra, future_dec : (<Longitude 5.00000563 deg>, <Latitude -4.99998891 deg>)

Get More
========
The following pages show up some concrete examples of PyVO code consuming annotated VOTables provided by a
MIVOT-enable cone-search service.

.. toctree::
   :maxdepth: 2

   examples

Reference/API
=============

.. automodapi:: pyvo.mivot.viewer
.. automodapi:: pyvo.mivot.seekers
.. automodapi:: pyvo.mivot.features
.. automodapi:: pyvo.mivot.utils
