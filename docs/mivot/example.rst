*************************************
MIVOT (``pyvo.mivot``): Code Examples
*************************************

This section provides a few examples of how to use annotated data, as well as tips for creating annotations.

Photometric Properties Readout
==============================

This example is based on VOTables provided by the ``XTapDB`` service.
This service exposes the slim `4XMM dr14 catalogue <http://xmmssc.irap.omp.eu/>`_.
It  is able to map query responses on the fly to the MANGO data model. 
The annotation process only annotates the columns that are selected by the query.

The following properties are supported:

- ``mango:Brightness`` to which fluxes are mapped
- ``mango:Color`` to which hardness ratio are mapped
- ``mango:EpochPosition`` to which positions and first observation  dates are mapped
- ``mango:Status`` to which quality flags of the source detections are mapped

A specific response format (``application/x-votable+xml;content=mivot``) must be set in order
to tell the server to annotate the queried data.

(*Please read the comment inside the code snippet carefully to fully understand the process*)

 .. code-block:: python
 
    import pytest
    from pyvo.utils import activate_features
    from pyvo.dal import TAPService
    from pyvo.mivot.utils.xml_utils import XmlUtils
    from pyvo.mivot.utils.dict_utils import DictUtils
    from pyvo.mivot.viewer.mivot_viewer import MivotViewer
 
    # Enable MIVOT-specific features in the pyvo library
    activate_features("MIVOT")
 
    service = TAPService('https://xcatdb.unistra.fr/xtapdb')
    result = service.run_sync(
        """
        SELECT TOP 5 * FROM "public".mergedentry 
        """,
        format="application/x-votable+xml;content=mivot"
        )
 	
    # The MIVOT viewer generates the model view of the data
    m_viewer = MivotViewer(result, resolve_ref=True)   
     	
    # Print out the Mivot annotations read out of the VOtable
 	# This statement is just for a pedagogic purpose (access to a private attribute)
 	XmlUtils.pretty_print(m_viewer._mapping_block)
    

In this first step we just queried the service and we built the object that will process the Mivot annotations.
The Mivot block printing output is too long to be listed here. However, the screenshot below shows its shallow structure.

.. image:: _images/xtapdbXML.png
   :width: 500
   :alt: Shallow structure of the annotation block.

- The GLOBALS section contains all the coordinate systems (in a wide sense). This includes the allowed values for
  the detection flags and the photometric calibrations.
- The TEMPLATES section contains the objects to which table data is mapped. In this example, there is one
  ``MangoObject`` instance which holds all the mapped properties.
   
At instantiation time, the viewer reads the first data row, which must exist,
in order to construct a Python object that reflects the mapped model. 

 .. code-block:: python
  
    # Build a Python object matching the TEMPLATES content and 
    # which leaves are set with the values of the first row
    mivot_instance = m_viewer.dm_instance

    # Print out the content of the Python object
    # This statement is just for a pedagogic purpose
    DictUtils.print_pretty_json(mivot_instance.to_dict())

The annotations are consumed by this dynamic Python object which leaves are set with the data of the current row.
You can explore the structure of this object by using the printed dictionary or standard object paths as shown below.

Now, we can iterate through the table data and retrieve an updated Mivot instance for each row.

 .. code-block:: python

    while m_viewer.next():
        if mivot_instance.dmtype == "mango:MangoObject":
            print(f"Read source {mivot_instance.identifier.value} {mivot_instance.dmtype}")
            for mango_property in mivot_instance.propertyDock:
                if  mango_property.dmtype == "mango:Brightness":
                    if mango_property.value.value:
                        mag_value = mango_property.value.value
                        mag_error = mango_property.error.sigma.value
                        phot_cal = mango_property.photCal
                        spectral_location = phot_cal.photometryFilter.spectralLocation
                        mag_filter = phot_cal.identifier.value
                        spectral_location = phot_cal.photometryFilter.spectralLocation
                        mag_wl = spectral_location.value.value
                        sunit = spectral_location.unitexpression.value

                        print(f"  flux at {mag_wl} {sunit} (filter {mag_filter}) is {mag_value:.2e} +/- {mag_error:.2e}")

    Read source 4XMM J054329.3-682106 mango:MangoObject
      flux at 0.35 keV (filter XMM/EPIC/EB1) is 8.35e-14 +/- 3.15e-14
      flux at 0.75 keV (filter XMM/EPIC/EB2) is 3.26e-15 +/- 5.45e-15
      flux at 6.1 keV (filter XMM/EPIC/EB8) is 8.68e-14 +/- 6.64e-14
    ...
    ...

The same code can easily be connected with matplotlib to plot SEDs as shown below (code not provided).
  

.. image:: _images/xtapdbSED.png
   :width: 500
   :alt: XMM SED
   
It is to noted that the current table row keeps available through the Mivot viewer.

 .. code-block:: python

    row = m_viewer.table_row


.. important::
   The code shown in this example can be used with any VOTable that has data mapped to MANGO.
   It contains no features specific to the XtatDB output.

   This is exactly the purpose of the MIVOT/MANGO abstraction layer: to allow the same processing
   to be applied to any annotated VOTable.

   The same client code can be reused in many places with many datasets, provided they are annotated.

Epoch Position Readout
======================

This example is based on a VOtable resulting on a Vizier cone search.
This service maps the data to  the ``EpochPosition`` MANGO property, 
which models a full source's  astrometry at a given date.


.. warning::
   At the time of writing, Vizier only mapped positions and proper motions (when  available),
   and the definitive epoch class had not been adopted.
   Therefore, this implementation may differ a little bit from the standard model.
   
   Vizier does not wrap the source properties in a MANGO object,
   but rather lists them in the Mivot *TEMPLATES*. 
   The annotation reader must support both designs.

In the first step below, we run a standard cone search query by using the standard PyVO API.

 .. code-block:: python
 
    import pytest
    import astropy.units as u
    from astropy.coordinates import SkyCoord
    from pyvo.dal.scs import SCSService

    from pyvo.utils import activate_features
    from pyvo.mivot.viewer.mivot_viewer import MivotViewer
    from pyvo.mivot.features.sky_coord_builder import SkyCoordBuilder
    from pyvo.mivot.utils.dict_utils import DictUtils

    # Enable MIVOT-specific features in the pyvo library
    activate_features("MIVOT")
    
    scs_srv = SCSService(" https://vizier.cds.unistra.fr/viz-bin/conesearch/V1.5/I/239/hip_main")

    query_result = scs_srv.search(
        pos=SkyCoord(ra=52.26708 * u.degree, dec=59.94027 * u.degree, frame='icrs'),
        radius=0.5)

    # The MIVOt viewer generates the model view of the data
    m_viewer = MivotViewer(query_result, resolve_ref=True)

Once the query is finished, we can create the object that will process the Mivot annotations.

 .. code-block:: python
  
    # Build a Python object matching the TEMPLATES content and 
    # which leaves are set with the values of the first row
    mivot_instance = m_viewer.dm_instance

    # Print out the content of the Python object
    # This statement is just for a pedagogic purpose
    DictUtils.print_pretty_json(mivot_instance.to_dict())

The annotations are consumed by this dynamic Python object which leaves are set with the data of the current row.
You can explore the structure of this object by using standard object paths or by browsing the dictionary shown below.

 .. code-block:: json
 
	{
	  "dmtype": "mango:EpochPosition",
	  "longitude": {
	    "dmtype": "ivoa:RealQuantity",
	    "value": 51.64272638,
	    "unit": "deg"
	  },
	  "latitude": {
	    "dmtype": "ivoa:RealQuantity",
	    "value": 60.28156089,
	    "unit": "deg"
	  },
	  "pmLongitude": {
	    "dmtype": "ivoa:RealQuantity",
	    "value": 13.31,
	    "unit": "mas/yr"
	  },
	  "pmLatitude": {
	    "dmtype": "ivoa:RealQuantity",
	    "value": -23.43,
	    "unit": "mas/yr"
	  },
	  "epoch": {
	    "dmtype": "ivoa:RealQuantity",
	    "value": 1991.25,
	    "unit": "yr"
	  },
	  "parallax": {
	    "dmtype": "ivoa:RealQuantity",
	    "value": 5.12,
	    "unit": "mas"
	  },
	  "spaceSys": {
	    "dmtype": "coords:SpaceSys",
	    "dmid": "SpaceFrame_ICRS",
	    "dmrole": "mango:EpochPosition.spaceSys",
	    "frame": {
	      "dmrole": "coords:PhysicalCoordSys.frame",
	      "dmtype": "coords:SpaceFrame",
	      "spaceRefFrame": {
	        "dmtype": "ivoa:string",
	        "value": "ICRS"
	      }
	    }
	  }
	}   

 
 The reader can transform ``EpochPosition`` instances into ``SkyCoord`` instances.
 These can then be used for further scientific processing.
   
 .. code-block:: python
 
    while m_viewer.next():
       if mivot_instance.dmtype == "mango:EpochPosition":
           scb = SkyCoordBuilder(mivot_instance.to_dict())
           # do whatever process with the SkyCoord object
           print(scb.build_sky_coord())

.. important::
   Similar to the previous example, this code can be used with any VOTable with data mapped to MANGO.
   It contains no features specific to the Vizier output.
   
   It avoids the need for users to build SkyCoord objects by hand from VOTable fields,
   which is never an easy task.
 
 
The next section provides some tips to use the API documented in the annoter `page <annoter.html>`_.

Annotation Tips (server side)
=============================

The annotation process is intended to be performed at the server level.
How it is implemented depends on the related DAL protocol, the framework used,
and the available metadata.
This process likely occurs before the data table is streamed out because
the Mivot block must precede the TABLE block.
This means it cannot use the table FIELDs, but rather some internal representation.

However, the examples below use the FIELDs to demonstrate how an annotation task could work.


Map a magnitude to a Mango Brightness
=====================================

Assuming that our dataset has the two following fields, let's map the magnitude in the J band
to the ``mango:Brightness`` class.

 .. code-block:: xml
 
    <FIELD name="Jmag" ucd="phot.mag;em.IR.J" datatype="float" width="6" precision="3" unit="mag">
      <DESCRIPTION>?(jmag) 2MASS J-band magnitude</DESCRIPTION>
    </FIELD>
    <FIELD name="e_Jmag" ucd="stat.error;phot.mag" datatype="float" width="6" precision="3" unit="mag">
      <DESCRIPTION>?(ejmag) Error on Jmag</DESCRIPTION>
    </FIELD>
 
The MANGO brightness class packs together 3 components: the magnitude, its error and the photometric calibration.
 
Mivot serializations of the photometric calibrations are given by the SVO `Filter Profile Service <https://svo2.cab.inta-csic.es/svo/theory/fps/>`_.
The first thing to do is to get the FPS identifier of the searched filter (2MASS J in our case).

Once the filter is selected, the identifier of the calibration in the desired system can by copied from the 
`FPS <https://svo2.cab.inta-csic.es/svo/theory/fps/index.php?id=2MASS/2MASS.J&&mode=browse&gname=2MASS&gname2=2MASS#filter>`_
page as shown below.  

.. image:: _images/filterProfileService.png
   :width: 500
   :alt: FPS screen shot.


Now, we can build the mapping parameters and apply them to add the mapping of that property.

 .. code-block:: python
 
    votable = parse("SOME/VOTABLE/PATH")
    builder = InstancesFromModels(votable, dmid="URAT1")

    # Add the mapping of a brightness property
    builder.add_mango_brightness( photcal_id="2MASS/2MASS.J/Vega",
            mapping={"value": "Jmag",
                     "error": { "class": "PErrorSym1D", "sigma": "e_Jmag"}
                     },
            semantics={"description": "magnitude J",
                       "uri": "https://www.ivoa.net/rdf/uat/2024-06-25/uat.html#magnitude",
                       "label": "magnitude"})

    
    # Once all all properties have been mapped, we can
    # tell the builder to complete the mapping block    
    builder.pack_into_votable()

The mapping parameters can be interpreted that way:
 
 - The photometric calibration match the ``2MASS/2MASS.J/Vega`` FPS output
 - The magnitude is given by the FIELD identified by  ``Jmag``
 - The magnitude error, which is symmetrical, is given by the FIELD identified by  ``e_Jmag``
 - The optional semantics block of the property (see the MANGO specification) indicates that the
   property is a magnitude.
 

Map an data to a Mango EpochPosition
====================================

The mapping of any property follow the same schema but with specific mapping parameters.
As it turns out, the EpochPosition can be very complex, with six parameters, their errors and their correlations.

If the VOTable fields are available during the annotation process, the API can extract a template of the mapping parameters.

 .. code-block:: python
 
    scs_srv = SCSService(" https://vizier.cds.unistra.fr/viz-bin/conesearch/V1.5/I/239/hip_main")

    query_result = scs_srv.search(
        pos=SkyCoord(ra=52.26708 * u.degree, dec=59.94027 * u.degree, frame='icrs'),
        radius=0.5)

    builder = InstancesFromModels(query_result.votable, dmid="URAT1")
    
    # Get a mapping proposal based on the FIELD UCDs
    parameters = builder.extract_epoch_position_parameters()
    DictUtils.print_pretty_json(parameters)

The JSON below shows the detected mapping parameters as a dictionary whose structure matches that expected by the API.
  
 .. code-block:: json
 
	 {
	  "frames": {
	    "spaceSys": {
	      "dmid": "_spaceframe_ICRS_BARYCENTER"
	    },
	    "timeSys": {}
	  },
	  "mapping": {
	    "longitude": "t1_c8",
	    "latitude": "t1_c9",
	    "parallax": "t1_c11",
	    "pmLongitude": "t1_c12",
	    "pmLatitude": "t1_c13",
	    "errors": {
	      "properMotion": {
	        "class": "PErrorSym2D",
	        "sigma1": "e_pmRA",
	        "sigma2": "e_pmDE"
	      }
	    },
	    "correlations": {}
	  },
	  "semantics": {
	    "description": "6 parameters position",
	    "uri": "https://www.ivoa.net/rdf/uat/2024-06-25/uat.html#astronomical-location",
	    "label": "Astronomical location"
	  }
	}
 
This template can be updated manually or by any other means, and then used to adjust the "EpochPosition" mapping.
 
 .. code-block:: python
    
    # Add the EpochPosition to the annotations with the modified mapping parameters
    builder.add_mango_epoch_position(**parameters)
    builder.pack_into_votable()
    
  