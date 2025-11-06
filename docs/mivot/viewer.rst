******************************************************
MIVOT (``pyvo.mivot``): Annotation Viewer - Public API
******************************************************


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
    tables of the VOTable (get more in  :doc:`index`).

Using the API
=============

 .. attention::
	The module based on XPath queries and allowing to browse the XML
	annotations (``viewer.XmlViewer``)  has been removed from version 1.8
	
Integrated Readout
------------------
The ``ModelViewer`` module manages access to data mapped to a model through dynamically
generated objects (``MivotInstance`` class).

These objects can be used as standard Python instances, with the fields representing model elements.
They can also be used as Python dictionaries (provided by the ``to_dict()`` method), with the keys
representing the model elements. 

The code below, based on the processing of a cone-search output, demonstrates both uses.

The first step is to instanciate a viewer that will provide the API for browsing annotations.
The viewer can be built from a VOTable file path, a parsed VOtable (``VOTableFile`` object),
or a ``DALResults`` instance.

.. code-block:: python

   import pytest
   import astropy.units as u
   from astropy.coordinates import SkyCoord
   from pyvo.dal.scs import SCSService
   from pyvo.utils.prototype import activate_features
   from pyvo.mivot.version_checker import check_astropy_version
   from pyvo.mivot.viewer.mivot_viewer import MivotViewer
   
   activate_features("MIVOT")
   if check_astropy_version() is False:
       pytest.skip("MIVOT test skipped because of the astropy version.")
       
   scs_srv = SCSService("https://vizier.cds.unistra.fr/viz-bin/conesearch/V1.5/I/239/hip_main")
   m_viewer = MivotViewer(
       scs_srv.search(
            pos=SkyCoord(ra=52.26708 * u.degree, dec=59.94027 * u.degree,
                         frame='icrs'),
            radius=0.1
            ),
       resolve_ref=True
       )

In this example, the query result is mapped to the ``mango:EpochPosition`` class,
but users do not need to know this in advance, since the API provides tools
to discover the mapped models.

.. code-block:: python
	
   if m_viewer.get_models().get("mango"):
       print("data is mapped to the MANGO data model")      
.. code-block:: text
	
   data is mapped to the MANGO data model

We can also check which datamodel classes the data is mapped to.

.. code-block:: python

   mivot_instances = m_viewer.dm_instances
   print(f"data is mapped to {len(mivot_instances)} model class(es)")
   mivot_instance = m_viewer.dm_instances[0]
   print(f"data is mapped to the {mivot_instance.dmtype} class")
.. code-block:: text
	
   data is mapped to 1 model clsss(es)
   data is mapped to the mango:EpochPosition class

At this point, we know that the data has been mapped to the ``MANGO`` model,
and that the data rows can be interpreted as instances of the ``mango:EpochPosition``. 

.. code-block:: python
	
   print(mivot_instance.spaceSys.frame.spaceRefFrame.value)
   while m_viewer.next_row_view():
      print(f"position: {mivot_instance.latitude.value} {mivot_instance.longitude.value}")

.. code-block:: text
	
   ICRS
   position: 59.94033461 52.26722684
   ...
    
.. important::
	
   Coordinate systems are usually mapped in the GLOBALS MIVOT block. 
   This allows them to be referenced from any other MIVOT element. 
   The viewer resolves such references when the constructor flag ``resolve_ref`` is set to ``True``.
   In this case the coordinate system instances are copied into their host elements.    

The code below shows how to access GLOBALS instances independently of the mapped data.

.. code-block:: python

   for globals_instance in m_viewer.dm_globals_instances():
       print(globals_instance)
       
.. code-block:: json
	
    {
      "dmtype": "coords:SpaceSys",
      "dmid": "SpaceFrame_ICRS",
      "frame": {
        "dmrole": "coords:PhysicalCoordSys.frame",
        "dmtype": "coords:SpaceFrame",
        "spaceRefFrame": {
          "dmtype": "ivoa:string",
          "value": "ICRS"
        }
      }
    }

As you can see from the previous examples, model leaves (class attributes) are complex types.
This is because they contain additional metadata as well as values:

- ``value``: attribute value
- ``dmtype``: attribute type such as defined in the Mivot annotations
- ``unit``: attribute unit such as defined in the Mivot annotations

The model view on a data row can also be passed as a Python dictionary
using the ``to_dict()`` property of ``MivotInstance``.

.. code-block:: python

   from pyvo.mivot.utils.dict_utils import DictUtils

    mivot_object = m_viewer.dm_instance
    mivot_object_dict = mivot_object.to_dict()
    DictUtils.print_pretty_json(mivot_object_dict)
 
.. code-block:: json
	
	{
        "dmtype": "EpochPosition",
        "longitude": {"value": 359.94372764, "unit": "deg"},
        "latitude": {"value": -0.28005255, "unit": "deg"},
        "pmLongitude": {"value": -5.14, "unit": "mas/yr"},
        "pmLatitude": {"value": -25.43, "unit": "mas/yr"},
        "epoch": {"value": 1991.25, "unit": "year"},
        "Coordinate_coordSys": {
            "dmtype": "SpaceSys",
            "dmid": "SpaceFrame_ICRS",
            "dmrole": "coordSys",
            "spaceRefFrame": {"value": "ICRS"},
        },
    }

The ``to_hk_dict()`` method extends the model leaves with the references of the mapped columns.

- It is recommended to work with deep copies of the
  dictionaries as they are rebuilt each time the ``to_dict()`` property is invoked.
- The Python representation (``__repr__()``) of ``MivotInstance`` instances is made with a pretty
  string serialization of this dictionary.

Per-Row Readout
---------------

The annotation schema can also be applied to table rows read outside of the ``MivotViewer``
with the `astropy.io.votable` API:

.. code-block:: python

    votable = parse(path_to_votable)
    table = votable.resources[0].tables[0]
    # init the viewer on the first resource of the votable (default)
    mivot_viewer = MivotViewer(votable)
    mivot_object = mivot_viewer.dm_instance
    # and feed it with the numpy table row
    for rec in table.array:
        # apply the mapping to current row
        mivot_object.update(rec)
        # show that the model retrieve the correct values
        # ... or do whatever you want 
        assert rec["RAICRS"] == mivot_object.longitude.value
        assert rec["DEICRS"] == mivot_object.latitude.value

Mivot/Mango as a Direct Gateway from Data to Astropy SkyCoord
-------------------------------------------------------------

A simple way to get the most out of annotations is to use them
to directly create Astropy objects, without having to parse the metadata,
whether it comes from the annotation or the VOTable.

.. code-block:: python
    from pyvo.mivot.features.sky_coord_builder import SkyCoordBuilder

    m_viewer.rewind()
    while m_viewer.next_row_view():
        sky_coord_builder = SkyCoordBuilder(mivot_instance)
        sky_coord = sky_coord_builder.build_sky_coord()
        print(sky_coord)

.. code-block:: text
	
    <SkyCoord (ICRS): (ra, dec, distance) in (deg, deg, pc)
        (52.26722684, 59.94033461, 1315.7894902)
     (pm_ra_cosdec, pm_dec) in mas / yr
        (-0.82, -1.85)>

In the above example, we assume that the mapped model can be used as a ``SkyCoord`` precursor. 
If this is not the case, an error is raised.

.. important::
	
   In the current implementation, the only functioning gateway connects 
   ``Mango::EpochPosition`` objects with the ``SkyCoord`` class. In future,
   we will implement the same mechanism for any property modelled by Mango,
   as well as potentially for other IVOA models.

Class Generation in a Nutshell
------------------------------

MIVOT reconstructs model structures with 3 elements:

- ``INSTANCE`` for the objects
- ``ATTRIBUTE`` for the attributes
- ``COLLECTION`` for the elements with a cardinality greater than 1

The role played by each of these elements in the model hierarchy is defined
by its ``@dmrole`` XML attribute. Types of both ``INSTANCE`` and ``ATTRIBUTE`` are defined by
their ``@dmtype`` XML attributes.

``MivotInstance`` classes are built by following MIVOT annotation structure:

- ``INSTANCE`` are represented by Python classes
- ``ATTRIBUTE`` are represented by Python class fields
- ``COLLECTION`` are represented by Python lists ([])

``@dmrole`` and ``@dmtype`` cannot be used as Python keywords as such, because they are built from VO-DML
identifiers, which have the following structure: ``model:a.b``.

- Only the last part of the path is kept for attribute names.
- For class names, forbidden characters (``:`` or ``.``) are replaced with ``_``.
- Original ``@dmtype`` are kept as attributes of generated Python objects.
- The structure of the ``MivotInstance`` objects can be inferred from the mapped model in 2 different ways:

  - 1.  From the MIVOT instance property ``MivotInstance.to_dict()`` a shown above.
        This is a pure Python dictionary but its access can be slow because it is generated
        on the fly each time the property is invoked.
  - 2.  From the internal  class dictionary ``MivotInstance.__dict__``
        (see the Python `data model <https://docs.python.org/3/reference/datamodel.html>`_).

.. code-block:: python

   mivot_instance = mivot_viewer.dm_instance

   print(mivot_instance.__dict__.keys())
   # dict_keys(['dmtype', 'longitude', 'latitude', 'pmLongitude', 'pmLatitude', 'epoch', 'Coordinate_coordSys'])

   print(mivot_instance.Coordinate_coordSys.__dict__.keys())
   # dict_keys(['dmtype', 'dmid', 'dmrole', 'spaceRefFrame'])

   print(mivot_instance.Coordinate_coordSys.spaceRefFrame.__dict__.keys())
   # dict_keys(['dmtype', 'value', 'unit', 'ref'])


*More examples can be found* :ref:`here <mivot-examples>`.

Reference/API
=============

.. automodapi:: pyvo.mivot.viewer
