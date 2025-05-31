***************************************************
MIVOT (``pyvo.mivot``): Annotation Writer - Dev API
***************************************************

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
    tables of the VOTable (get more in :doc:`index`).

- Model Instances in VOTables is a VO `standard <https://ivoa.net/documents/MIVOT/20230620/REC-mivot-1.0.pdf>`_
- Requires Astropy>=6.0
- ``pyvo.mivot`` is a prototype feature which must be activated with ``activate_features("MIVOT")``

Use the API
===========

Build Annotation Object per Object
----------------------------------

This documentation is intended for developers of data model classes who want to map them to VOTables
and not for end users. A future version will allow end users to create annotations with
ready-to-use data model building blocks.

Creating annotations consists of 3 steps:

#. Create individual instances  (INSTANCE) using the ``MivotInstance`` class: objects are
   built attribute by attribute. These components can then be aggregated into
   more complex objects following the structure of the mapped model(s).
#. Wrap the annotations with the ``MivotAnnotations`` class: declare to the annotation builder
   the models used, and place individual instances at the right place (TEMPLATES or GLOBALS).
#. Insert the annotations into a VOtable by using the Astropy API (wrapped in the package logic).

The annotation builder does not check whether the XML conforms to any particular model.
It simply validates it against the MIVOT XML Schema if the ``xmlvalidator`` package if is installed.

The example below shows a step-by-step construction of a MIVOT block mapping
a position with its error (as defined in the ``MANGO`` draft)
and its space coordinate system (as defined in the ``Coordinates`` model and imported by ``MANGO``).

Build the empty MIVOT Block
^^^^^^^^^^^^^^^^^^^^^^^^^^^

- The MIVOT block consists of:

  - A process status
  - A list of mapped models
  - A list of globals, which are objects not associated with
    VOTable data and that can be shared by any other MIVOT instance.
  - A list of templates, which are objects that are connected to
    VOTable data and whose leaf values change from one row to another.

- ``MIVOT`` is still an experimental feature which must be activated

.. code-block:: python


    from astropy.io.votable import parse
    from pyvo.utils import activate_features
    from pyvo.mivot.utils.exceptions import MappingException
    from pyvo.mivot.utils.dict_utils import DictUtils
    from pyvo.mivot.writer.annotations import MivotAnnotations
    from pyvo.mivot.writer.instance import MivotInstance
    from pyvo.mivot.viewer.mivot_viewer import MivotViewer

    activate_features("MIVOT")

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
    mivot_annotations.set_report(True, "PyVO Tuto")

Build the Coordinate System Object
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The space coordinate system is made of a space frame and a reference position, both wrapped in a ``coords:SpaceSys``
object (see the `Coordinates <https://ivoa.net/documents/Coords/20221004/index.html>`_ data model).

The time coordinate system is made of a time frame and a reference position, both wrapped in a ``coords:TimeSys``
object.

- Each of these objects have a ``dmid`` which will be used as a reference by the ``EpochPosition`` instance.

.. code-block:: python


    mivot_annotations.add_simple_space_frame(ref_frame="FK5",
                                             ref_position="BARYCENTER",
                                             equinox="J2000",
                                             dmid="_spacesys"
                                             )
    mivot_annotations.add_simple_time_frame(ref_frame="TCB",
                                            ref_position="BARYCENTER",
                                            dmid="_timesys"
                                            )


Build the EpochPosition Object
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- In this example we only use the position attributes (RA/DEC) of the ``EpochPosition`` class.
- The reference to the space coordinate system is added at the end.
- The ``ref`` XML attributes reference columns that must be used to set the model attributes.
  Their values depend on the VOTable to be mapped.

.. code-block:: python


    from astropy.io.votable import parse
    from pyvo.utils import activate_features
    from pyvo.mivot.utils.exceptions import MappingException
    from pyvo.mivot.utils.dict_utils import DictUtils
    from pyvo.mivot.writer.annotations import MivotAnnotations
    from pyvo.mivot.writer.instance import MivotInstance
    from pyvo.mivot.viewer.mivot_viewer import MivotViewer

    activate_features("MIVOT")
    
    position = MivotInstance(dmtype="mango:EpochPosition")
    position.add_attribute(
        dmtype="ivoa:RealQuantity",
        dmrole="mango:EpochPosition.longitude",
        unit="deg",
        ref="RAICRS",
    )
    position.add_attribute(
        dmtype="ivoa:RealQuantity",
        dmrole="mango:EpochPosition.latitude",
        unit="deg",
        ref="DEICRS",
    )
    position.add_reference(
        dmref="_spacesys", dmrole="mango:EpochPosition.spaceSys"
    )


Build the Position Error
^^^^^^^^^^^^^^^^^^^^^^^^

- We assume that the position error is the same on both axes without correlation.
  In terms of MANGO error, this corresponds to a 2x2 diagonal error matrix with two equal coefficients.
- Finally, the error is added as a component of the ``EpochPosition`` instance.

.. code-block:: python


    epoch_position_error = MivotInstance(
        dmtype="mango:EpochPositionErrors", dmrole="mango:EpochPosition.errors"
    )
    position_error = MivotInstance(
        dmtype="mango:error.ErrorCorrMatrix",
        dmrole="mango:EpochPositionErrors.position",
    )
    position_error.add_attribute(
        dmtype="ivoa:RealQuantity",
        dmrole="mango:error.ErrorCorrMatrix.sigma1",
        unit="arcsec",
        ref="sigm",
    )
    position_error.add_attribute(
        dmtype="ivoa:RealQuantity",
        dmrole="mango:error.ErrorCorrMatrix.sigma2",
        unit="arcsec",
        ref="sigm",
    )
    epoch_position_error.add_instance(position_error)
    position.add_instance(epoch_position_error)


Pack the MIVOT Block
^^^^^^^^^^^^^^^^^^^^

- Pack the model instances previously built.
- The latest step (build_mivot_block) includes a validation of the MIVOT syntax that works only
  if the ``xmlvalidator`` package has been installed.

.. code-block:: python


    mivot_annotations.add_templates(position)
    mivot_annotations.build_mivot_block()


Insert the MIVOT Block in a VOTable
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- This straightforward step is based on the Astropy VOTable API.
- Annotations are stored in-memory (in the parsed VOtable).
- The mapping can be tested with the ``MivotViewer`` API (see the  :doc:`viewer`)
- The VOtable must be explicitly saved on disk if needed.

 .. code-block:: python


    from astropy.io.votable import parse

    votable = parse(votable_path)
    mivot_annotations.insert_into_votable(votable)

    mivot_viewer = MivotViewer(votable)
    mapped_instance = mivot_viewer.dm_instance

    votable.to_xml("pyvo-tuto.xml")


Validate the annotations against the models
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- This action requires the ``mivot-validatorXXX`` package to be installed.
- It validates the mapped classes against the models they come from.


 .. code-block:: shell


    % pip install mivot-validator
    % mivot-instance-validate pyvo-tuto.xml
    ...
    Valid if no error message
    ...

