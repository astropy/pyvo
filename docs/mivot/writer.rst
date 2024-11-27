.. code-block:: python
    :caption: Working with a model view as a dictionary
              (the JSON layout has been squashed for display purpose)

    from pyvo.mivot.utils.dict_utils import DictUtils

    mivot_instance = m_viewer.dm_instance
    mivot_object_dict = mivot_object.dict

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

- Model Instances in VOTables is a VO `standard <https://ivoa.net/documents/MIVOT/20230620/REC-mivot-1.0.pdf>`_
- Requires Astropy>=6.0
- ``pyvo.mivot`` is a prototype feature which must be activated with ``activate_features("MIVOT")``


Implementation Scope
--------------------
This implementation is totally model-agnostic.

- It does not operate any validation against specific data models.
- It just requires the annotation syntax being compliant with the standards.

.. code-block:: python
    :caption: Build an annotation block, add used models and set mapping report
    
    from pyvo.mivot.writer.annotations import MivotAnnotations
    
    mivot_annotations = MivotAnnotations()
    mivot_annotations.add_model(
        "ivoa", "https://www.ivoa.net/xml/VODML/IVOA-v1.vo-dml.xml"
    )
    mivot_annotations.add_model(
        "coords", "https://www.ivoa.net/xml/STC/20200908/Coords-v1.0.vo-dml.xml"
    )
    mivot_annotations.add_model(
        "mango",
        "https://raw.githubusercontent.com/lmichel/MANGO/draft-0.1/vo-dml/mango.vo-dml.xml",
    )
    mivot_annotations.set_report(True, "Mivot writer unit test")

    from pyvo.mivot.utils.dict_utils import DictUtils

    mivot_instance = m_viewer.dm_instance
    mivot_object_dict = mivot_object.dict

blabla
must be constructed in the good order.

.. code-block:: python
    :caption: Build the coordinate system (coords:SpaceSys)
    
    space_sys = MivotInstance(dmid="_spacesys_icrs", dmtype="coords:SpaceSys")
    space_frame = MivotInstance(
        dmrole="coords:PhysicalCoordSys.frame", dmtype="coords:SpaceFrame"
    )
    space_frame.add_attribute(
        dmrole="coords:SpaceFrame.spaceRefFrame", dmtype="ivoa:string", value="ICRS"
    )
    ref_position = MivotInstance(
        dmrole="coords:SpaceFrame.refPosition", dmtype="coords:StdRefLocation"
    )
    ref_position.add_attribute(
        dmrole="coords:StdRefLocation.position",
        dmtype="ivoa:string",
        value="BARYCENTER",
    )
    space_frame.add_instance(ref_position)
    space_sys.add_instance(space_frame)
    mivot_annotations.add_globals(space_sys)
