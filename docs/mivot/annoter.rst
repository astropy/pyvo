******************************************************
MIVOT (``pyvo.mivot``): Annotation Writer - Public API
******************************************************

This API allows to easily map VOTable data to recommended VO models, especially MANGO.
Only a little knowledge of the models is required

Mango is a model designed to enhance the description of table data in a way that each table
row can be interpreted as a Mango Object.
Mango objects are made of a property container, a description of the data origin and links on other Mango objects (not implemented yet).

In this current implementation, only a few properties are supported (Epoch position and photometry)
and the data origin can be added as literal values (not connected with table data). 

The pseudo codes below show the way to use this API.

The first step is to create the Annotation Builder and connect it to the VOTable to be annotated.

 .. code-block:: python

    votable = parse("MY/VOTABLE")
    builder = InstancesFromModels(votable, dmid="DR3Name")

The builder is then ready to get the properties to add to the Mango object.

 .. code-block:: python
 
     builder.add_mango_magnitude(photcal_id=photcal_id, mapping=mapping, semantics=semantics)
     builder.add_mango_magnitude(photcal_id=other_photcal_id, mapping=other_mapping, semantics=other_semantics)
     builder.add_mango_color(filter_ids=filter_ids, mapping=mapping, semantics=semantics)
     builder.add_mango_epoch_position(frames=frames, mapping=mapping, semantics=semantics)

We can now add the description of the data origin. 

 .. code-block:: python
 
     builder.add_query_origin(...mapping...)
 
- The order in which the components are added does not matter.
- The details of the parameters are described below.

Now the MIVOT block can be completed and inserted into the VOtable.


 .. code-block:: python
 
    builder.pack_into_votable()
    votable.to_xml("MYY/ANNOTATED/VOTABLE")

About Parameters
================

Mappings are always given as dictionaries, where keys are the model roles and values
are either column names or literal values.

The lists of supported roles are given in the :py:mod:`pyvo.mivot.glossary`.

The (3) functions adding properties have all 3 arguments

- ``filter/frame``: Map of the coordinate systems or photometric calibrations that apply to the property.
  All values specified here are considered literal. 
  The corresponding Mivot instances are placed in the GLOBALS block.
- ``Mapping``: Mapping of the table data to the property attributes. 
  The fine structure of these dictionaries is specific to each mapped class,
  but all follow the same pattern.
  Values specified as strings are considered to be column identifiers,
  unless the string starts with a '*'. In this case, the stripped string is taken as the literal value.
  Other value types (numeric or boolean) are all considered literals. 
- ``semantics``: Semantic tags (text + vocabulary entry) that apply to the property.
  All values specified here are considered literal values. 
- All query origin parameters are considered as literals 

Add Query origin
----------------

Add the Mango ``QueryOrigin`` instance to the current ``MangoObject``.

.. figure:: _images/mangoDataOrigin.png
   :width: 500
   
   
   DataOrigin package of Mango.


``QueryOrigin`` is the object grouping together all the components needed to model the origin
of the MangoObject.

.. code-block:: python

    builder.add_query_origin(mapping)


The detail of the ``mapping`` parameter is given in the `pyvo.mivot.writer.InstancesFromModels.add_query_origin` documentation 
    
Add Properties
--------------

The main purpose of the ``MangoObject`` is to gather various properties that qualify the data row.

- The properties are stored in a container named ``propertyDock``. 
- During he annotation process, properties are added one by one by specific methods. 
- Only Photometry and EpochPosition are supported yet.


.. figure:: _images/mangoProperties.png
   :width: 500
   
   
   Properties supported by Mango.

Add EpochPosition
^^^^^^^^^^^^^^^^^

The ``EpochPosition`` property describes the astrometry of a moving source.
It handles six parameters (position, proper motion, parallax and radial velocity)
with their correlations and errors and the coordinate system for bot space and time axis.

.. code-block:: python

    builder.add_epoch_position(frames, mapping, semantics)

The detail of the parameters is given with the description of the 
:py:meth:`pyvo.mivot.writer.InstancesFromModels.add_mango_epoch_position` method.



Add Brightness
^^^^^^^^^^^^^^

The ``Brightness`` attaches to a flux or a magnitude with an error and a photometric calibration.

.. code-block:: python

    builder.add_mango_brightness(photcal_id, mapping, semantics)

The detail of the parameters is given with the description of the 
 :py:meth:`pyvo.mivot.writer.InstancesFromModels.add_mango_brightness` method.

Add Color
^^^^^^^^^

The ``Color`` attaches to a Color index or an hardness ratio value with an error and two photometric filters.

.. code-block:: python

    builder.add_mango_color(filter_idsn, mapping, semantics)

The detail of the parameters is given with the description of the 
 :py:meth:`pyvo.mivot.writer.InstancesFromModels.add_mango_color` method.


Reference/API
=============

.. automodapi:: pyvo.mivot.writer

.. automodapi:: pyvo.mivot.utils

.. automodapi:: pyvo.mivot.glossary
