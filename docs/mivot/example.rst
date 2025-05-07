*****************************************
MIVOT (``pyvo.mivot``): Roundtrip Example
*****************************************

This code example show how the MIVOT API can be used on both server and client sides.

- **Server side**: map a query response to Mango with Mivot annotations

  - Map the data to the ``EpochPosition`` Mango class.
  - Pack the annotation into a ``MangoObject`` so that we have one object per row.  
  - The current implementation is not able to read more than one object per row,
    although this is allowed by MIVOT.
- **Client side**: extract ``SkyCoord`` instances from these annotations 




Annotation Process (server side)
================================

Let's start by retrieving and parsing a regular VOTable from the Vizier Cone search service.

 .. code-block:: python

    import astropy.units as u
    from astropy.coordinates import SkyCoord
    from pyvo.dal.scs import SCSService

    from pyvo.utils import activate_features
    from pyvo.mivot.utils.xml_utils import XmlUtils
    from pyvo.mivot.writer.instances_from_models import InstancesFromModels
    from pyvo.mivot.viewer.mivot_viewer import MivotViewer
    from pyvo.mivot.features.sky_coord_builder import SkyCoordBuilder

    from pyvo.mivot.utils.dict_utils import DictUtils

    scs_srv = SCSService(
        "http://viz-beta.u-strasbg.fr/viz-bin/conesearch/I/239/hip_main"
        )

    query_result = scs_srv.search(
        pos=SkyCoord(
            ra=52.26708 * u.degree, dec=59.94027 * u.degree, frame='icrs'
            ),
        radius=0.5)

    votable = query_result.votable


This example works with a VOTable provided by an external service,
but in reality the annotation process must be done at the server
level as a step of producing the response to the current query.

We can now ask the MIVOT API to annotate the VOTable.

 .. code-block:: python

    builder = InstancesFromModels(votable, dmid="HIP")
    parameters = builder.extract_epoch_position_parameters()
    builder.add_mango_epoch_position(**parameters)

    builder.pack_into_votable()
    # This optional statement allows you to check 
    # the generated mapping with the naked eye.
    XmlUtils.pretty_print(builder.mivot_block)

We take the column "HIP" (ID or name) as the Mango object
identifier (role ``mango:MangoObject.identifier``).
The choice of the identifier column will be automated in a future release.

Mapping the data to the EpochPosition class is a 2-step process:

- We first extract the mapping rules from the metadata

  - VOTable COOSYS and TIMESYS are mapped to space/time coordinate systems (Coords DM)
  - Property semantics is hard coded (https://www.ivoa.net/rdf/uat/2024-06-25/uat.html#astronomical-location)
  - The (first) table columns are browsed to be associated with ``EpochPosition`` attributes.
- and then provide the annoter with them.

The reason for dividing the process in 2 steps is that the mapping rules may need to be fixed or completed by hand,
for example by adding missing metadata.

 
Annotation Readout (client side)
================================

The following readout code is disconnected from any specific VOTable.
It can be applied to any annotated dataset which is exactly the goal
of the data model annotation: a better interoperability.

 .. code-block:: python
    
    m_viewer = MivotViewer(votable, resolve_ref=True)
    mivot_instance = m_viewer.dm_instance

    # This optional statement allows you to check
    # the mapping extraction with the naked eye.
    DictUtils.print_pretty_json(mivot_instance.to_dict())
    
    while m_viewer.next():
        if mivot_instance.dmtype == "mango:MangoObject":
            print(f"--- Read source {mivot_instance.identifier.value}")
            for mango_property in mivot_instance.propertyDock:
                if mango_property.dmtype == "mango:EpochPosition":
                    scb = SkyCoordBuilder(mango_property.to_dict())
                    print(scb.build_sky_coord())

- We create a viewer instance associated with the parsed VOTable.
  It could also be associated with a DAL response.
- Then we create a Mivot instance, which is a dynamic Python object whose structure
  matches the mapped object (``MangoObject`` in our case).
- This Python object is updated as the data row is read.
- It is finally transformed in a SkyCoord instance (if possible).