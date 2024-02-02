*********************************
MIVOT (`pyvo.mivot`) Code example
*********************************

This page contains the code that has been used to validate the ``mivot`` package with some comments.
It was important to be able to test the ``mivot`` code on a live service in addition
to the static VOtables used for the unit tests.
This service has been deployed as a beta service by Vizier and it might not exist anymore at the time of reading.

Vizier Service
==============
This service is a cone-search able to access any of the Vizier tables and catalogs.
It is located at ``http://viz-beta.u-strasbg.fr/viz-bin/mivotconesearch/``
and it can be invoked that way: ``URL/CATALOG_ID?VO_SCS_PARAMS``.
The annotation processor maps the searched data on the ``MANGO:EpochPosition`` class.
5 parameters can be mapped (position, proper motion and epoch) which is enough to compute the epoch propagation.

The ``MANGO`` model is not a standard at the time of writing but this has no impact one the 3 first levels which are model agnostic.
The model dependency is more important for the 4st level, and if ``MANGO`` were to be changed, a new module should
be added to the ``feature`` package.


.. code-block:: xml
  :caption: Example of mapping block genrated by the Vizier cone-search

   <VODML xmlns="http://www.ivoa.net/xml/mivot">
      <REPORT status='OK'/>
      <MODEL name="mango"/>
      <MODEL name="ivoa" url="https://www.ivoa.net/xml/VODML/IVOA-v1.vo-dml.xml"/>
      <GLOBALS>
        <INSTANCE dmtype="coords:SpaceSys" dmid="SpaceFrame_ICRS">
          <ATTRIBUTE dmrole="coords:SpaceFrame.spaceRefFrame" dmtype="coords:SpaceFrame" value="ICRS"/>
        </INSTANCE>
      </GLOBALS>
      <TEMPLATES tableref="I/329/urat1">
        <INSTANCE dmtype="mango:EpochPosition">
          <ATTRIBUTE dmrole="mango:EpochPosition.longitude" dmtype="ivoa:RealQuantity" ref="RAICRS" unit="deg"/>
          <ATTRIBUTE dmrole="mango:EpochPosition.latitude" dmtype="ivoa:RealQuantity" ref="DEICRS" unit="deg"/>
          <ATTRIBUTE dmrole="mango:EpochPosition.pmLongitude" dmtype="ivoa:RealQuantity" ref="pmRA" unit="mas/year"/>
          <ATTRIBUTE dmrole="mango:EpochPosition.pmLatitude" dmtype="ivoa:RealQuantity" ref="pmDE" unit="mas/year"/>
          <ATTRIBUTE dmrole="mango:EpochPosition.epoch" dmtype="ivoa:RealQuantity" ref="_tab1_8" unit="yr"/>
          <REFERENCE dmrole="coords:Coordinate.coordSys" dmref="SpaceFrame_ICRS"/>
        </INSTANCE>
      </TEMPLATES>
   </VODML>

Connect the service
===================
The code below is a basic ``PyVO`` script that runs a cone-search query.

- The query result (``DALResults`` subclass instance)  is directly given to the model viewer.
- The model viewer is able to read the table rows and to provide for each an instance of the mapped model.
- The generation of the model views is done in streaming mode, row per row.
- The way those instances are serialized depends on the viewer level that is operated.

It is to be noted the that the epoch propagation computation (`apply_space_motion`) raises a warning
due to the fact that no distance is provided to ``SkyCoord``. This is worked around by the warning filter.

.. doctest-remote-data::
   :caption: PyVO code running a query on the Vizier cone-search
    >>> import sys
    >>> from pyvo.dal.scs import  SCSService
    >>> from astropy.coordinates import SkyCoord
    >>> import astropy.units as u
    >>> from pyvo.mivot.viewer.model_viewer_level1 import ModelViewerLevel1
    >>> from pyvo.mivot.utils.dict_utils import DictUtils
    >>> from pyvo.mivot.utils.xml_utils import XmlUtils
    ... # Ignore the warnings emited by the Erfa package while computing the epoch propagation
    >>> if not sys.warnoptions: # doctest: +SKIP
    ...     import warnings # doctest: +SKIP
    ...     warnings.simplefilter("ignore") # doctest: +SKIP
    >>> scs_srv = SCSService('http://viz-beta.u-strasbg.fr/viz-bin/mivotconesearch/I/329/urat1') # doctest: +SKIP
    >>> m_viewer = ModelViewerLevel1( # doctest: +SKIP
    >>> scs_srv.search(
    ...     pos=SkyCoord(ra=52.26708*u.degree, dec=59.94027*u.degree, frame='icrs'),
    ...     radius=0.05)
    ...     ) # doctest: +SKIP

Level1: Get the XML Representation of the Model Instances
=========================================================
This level returns an XML ``TEMPLATES`` element (see the standard)  representing the mapping of the current table.
This means that each data row can be seen as an instance of the ``EpochPosition`` class of the ``MANGO`` model.
This instance has been set with values read from the current row:

- ``value`` attributes are set with the corresponding table values.
- The space frame has been copied from the `GLOBALS` to the current instance.
- The attribute ``col_index``, which is no part of the ``MIVOT`` standard, has been added to provide the column number.
  This feature can be useful in a debug context.
- The attribute ``field_unit`` which is no part of the ``MIVOT`` standard, has been added to provides the units read in the ``FIELD``.
  This feature has been added to check that the mapping units are consistent with those of the ``FIELD``.

.. doctest-remote-data::
    >>> while m_viewer.get_next_row_view(): # doctest: +SKIP
    >>>    XmlUtils.pretty_print(m_viewer._get_model_view())# doctest: +SKIP
    <TEMPLATES tableref="I/329/urat1">
      <INSTANCE dmtype="mango:EpochPosition">
        <ATTRIBUTE dmrole="mango:EpochPosition.longitude" dmtype="ivoa:RealQuantity" ref="RAICRS" unit="deg" col_index="2" field_unit="deg" value="52.3441606"/>
        <ATTRIBUTE dmrole="mango:EpochPosition.latitude" dmtype="ivoa:RealQuantity" ref="DEICRS" unit="deg" col_index="3" field_unit="deg" value="59.9673411"/>
        <ATTRIBUTE dmrole="mango:EpochPosition.pmLongitude" dmtype="ivoa:RealQuantity" ref="pmRA" unit="mas/yr" col_index="17" field_unit="mas / yr" value="-4.6"/>
        <ATTRIBUTE dmrole="mango:EpochPosition.pmLatitude" dmtype="ivoa:RealQuantity" ref="pmDE" unit="mas/yr" col_index="18" field_unit="mas / yr" value="7.3"/>
        <ATTRIBUTE dmrole="mango:EpochPosition.epoch" dmtype="ivoa:RealQuantity" ref="_tab1_8" unit="yr" col_index="8" field_unit="yr" value="2013.405"/>
        <INSTANCE dmtype="coords:SpaceSys" dmid="SpaceFrame_ICRS" dmrole="coords:Coordinate.coordSys">
          <ATTRIBUTE dmrole="coords:SpaceFrame.spaceRefFrame" dmtype="coords:SpaceFrame" value="ICRS"/>
        </INSTANCE>
      </INSTANCE>
    </TEMPLATES>

The purpose of this level is to provide raw material for people developing APIs based on ``MIVOT``.
This is why the view getter is private (prefixed with a ``_``).

Leve2: Easy Browsing the Level1 Output
========================================
This level wraps the XML ``TEMPLATES`` provided by the level1 output to perform basic XPATH searches.

- Basically it allows to retrieve ``INSTANCE`` by either ``dmrole`` or ``dmtype`` or ``COLLECTION`` by ``dmrole``.
- The searched elements are returned as XML complex elements, as for level1.

.. doctest-remote-data::
    >>> row_view = m_viewer.get_next_row_view()) # doctest: +SKIP
    >>> m_viewer3 = m_viewer.get_level2() # doctest: +SKIP
    >>> XmlUtils.pretty_print(m_viewer3.get_instance_by_type("mango:EpochPosition", False)) # doctest: +SKIP
    <INSTANCE dmtype="mango:EpochPosition">
       <ATTRIBUTE dmrole="mango:EpochPosition.longitude" dmtype="ivoa:RealQuantity" ref="RAICRS" unit="deg" col_index="2" field_unit="deg" value="52.3441606"/>
       <ATTRIBUTE dmrole="mango:EpochPosition.latitude" dmtype="ivoa:RealQuantity" ref="DEICRS" unit="deg" col_index="3" field_unit="deg" value="59.9673411"/>
       <ATTRIBUTE dmrole="mango:EpochPosition.pmLongitude" dmtype="ivoa:RealQuantity" ref="pmRA" unit="mas/yr" col_index="17" field_unit="mas / yr" value="-4.6"/>
       <ATTRIBUTE dmrole="mango:EpochPosition.pmLatitude" dmtype="ivoa:RealQuantity" ref="pmDE" unit="mas/yr" col_index="18" field_unit="mas / yr" value="7.3"/>
       <ATTRIBUTE dmrole="mango:EpochPosition.epoch" dmtype="ivoa:RealQuantity" ref="_tab1_8" unit="yr" col_index="8" field_unit="yr" value="2013.405"/>
       <INSTANCE dmtype="coords:SpaceSys" dmid="SpaceFrame_ICRS" dmrole="coords:Coordinate.coordSys">
         <ATTRIBUTE dmrole="coords:SpaceFrame.spaceRefFrame" dmtype="coords:SpaceFrame" value="ICRS"/>
       </INSTANCE>
    </INSTANCE>

Level3: The Mapped Object as Python Instances
=============================================
The level3 viewer dynamically builds a Python class corresponding to the content of the ``TEMPLATE``.

- Instances of that class are provided by the ``mivot_class`` attribute of the viewer.
- Model fields can be accessed through class attributes.
- A global dictionary is also made available to allow users to discover the internal structure of the object.

.. doctest-remote-data::
    >>> row_view = m_viewer.get_next_row_view()):# doctest: +SKIP
    >>> m_viewer3 = m_viewer.get_level3() # doctest: +SKIP
    >>> print(m_viewer3.get_row_instance()) # doctest: +SKIP
    {'dmtype': 'EpochPosition', 'longitude': <pyvo.mivot.viewer.mivot_class.MivotClass object at 0x7fe267664700> ...}
    >>> print(f"Position {m_viewer3.mivot_class.latitude.value} {m_viewer3.mivot_class.longitude.value} deg") # doctest: +SKIP
    Position 59.9673411 52.3441606 deg

Feature: Epoch Propagation
==========================
At this level, implemented in the ``feature`` package, the viewer builds a ``SkyCoord`` instance from
the XML instance built from the mapping.
This instance can be used by any Astropy code as if it had been built in regular way.
The example below shows an epoch propagation computed by Astropy from the cone-search output.

.. doctest-remote-data::
   >>> while (row_view := m_viewer.get_next_row_view()): # doctest: +SKIP
   >>>     name_skycoo = row_view.epoch_propagation.sky_coordinate() # doctest: +SKIP
   >>>     print(f"In year {row_view.epoch.value}: ra={name_skycoo.ra.value} dec={name_skycoo.dec.value}") # doctest: +SKIP
   In year 2013.418: ra=52.2340018 dec=59.8937333
   >>>     later_skycoo = name_skycoo.apply_space_motion(dt=+10* u.yr) # doctest: +SKIP
   >>>     print(f"Ten year later: ra={later_skycoo.ra.value} dec={later_skycoo.dec.value}") # doctest: +SKIP
   Ten year later: ra=52.23401010665443 dec=59.89369913333254

It is to be noted that this feature depends on the model used.
