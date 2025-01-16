# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
This module contains test cases for validating the functionality of MivotInstance, MivotAnnotations,
and related components in the pyvo.mivot package. These tests ensure that the classes behave as
expected, including error handling and XML generation for data models.
"""

import os
import pytest
from astropy.io.votable import parse
from pyvo.utils import activate_features
from pyvo.mivot.version_checker import check_astropy_version
from pyvo.mivot.utils.exceptions import MappingError
from pyvo.mivot.utils.dict_utils import DictUtils
from pyvo.mivot.writer.annotations import MivotAnnotations
from pyvo.mivot.writer.instance import MivotInstance
from pyvo.mivot.viewer.mivot_viewer import MivotViewer

# Enable MIVOT-specific features in the pyvo library
activate_features("MIVOT")

# File paths for test data
votable_path = os.path.realpath(
    os.path.join(__file__, "..", "data", "test.mivot_viewer.no_mivot.xml")
)
data_path = os.path.realpath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")
)


def strip_xml(xml_string):
    """
    Strip unnecessary whitespace and newline characters from an XML string.

    Parameters:
    - xml_string (str): The XML string to strip.

    Returns:
    - str: The stripped XML string.
    """
    return (
        xml_string.replace("\n", "").replace(" ", "").replace("'", "").replace('"', "")
    )


@pytest.mark.skipif(not check_astropy_version(), reason="need astropy 6+")
def test_MivotInstance():
    """
    Test the MivotInstance class for various operations including attribute addition,
    reference addition, and XML generation. Verifies that invalid operations raise
    the expected MappingError.
    """
    with pytest.raises(MappingError):
        MivotInstance("")

    instance1 = MivotInstance("model:type.inst", dmid="id1")
    with pytest.raises(MappingError):
        instance1.add_attribute(
            dmrole="model:type.inst.role1", value="value1", unit="m/s"
        )
    with pytest.raises(MappingError):
        instance1.add_attribute(
            dmtype="model:type.att1", dmrole="model:type.inst.role1"
        )
    with pytest.raises(MappingError):
        instance1.add_reference(dmref="dmreference")
    with pytest.raises(MappingError):
        instance1.add_reference(dmrole="model:type.inst.role2")
    with pytest.raises(MappingError):
        instance1.add_instance("azerty")

    instance1.add_reference(dmrole="model:type.inst.role2", dmref="dmreference")
    instance1.add_attribute(
        dmtype="model:type.att1",
        dmrole="model:type.inst.role1",
        value="value1",
        unit="m/s",
    )
    assert strip_xml(instance1.xml_string()) == (
        "<INSTANCEdmtype=model:type.instdmid=id1>"
        + "<REFERENCEdmrole=model:type.inst.role2dmref=dmreference/>"
        + "<ATTRIBUTEdmtype=model:type.att1dmrole=model:type.inst.role1unit=m/svalue=value1/>"
        + "</INSTANCE>"
    )


@pytest.mark.skipif(not check_astropy_version(), reason="need astropy 6+")
def test_MivotAnnotations():
    """
    Test the MivotAnnotations class for template and global instance addition. Verifies
    that invalid operations raise the expected MappingError.
    """
    mb = MivotAnnotations()

    with pytest.raises(MappingError):
        mb.add_templates(12)
    with pytest.raises(MappingError):
        mb.add_globals(12)


@pytest.mark.skipif(not check_astropy_version(), reason="need astropy 6+")
def test_MivotInstanceAll():
    """
    Test the creation and combination of multiple MivotInstance objects, their attributes,
    references, and integration into a MivotAnnotations instance. Verifies correct XML
    generation and VOTable integration.
    """

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
    position.add_reference(
        dmref="_spacesys_icrs", dmrole="mango:EpochPosition.spaceSys"
    )
    position.add_instance(epoch_position_error)

    mivot_annotations = MivotAnnotations()
    mivot_annotations.add_model(
        "ivoa",
        vodml_url="https://www.ivoa.net/xml/VODML/IVOA-v1.vo-dml.xml"
    )
    mivot_annotations.add_model(
        "coords",
        vodml_url="https://www.ivoa.net/xml/STC/20200908/Coords-v1.0.vo-dml.xml"
    )
    mivot_annotations.add_model(
        "mango",
        vodml_url="https://raw.githubusercontent.com/lmichel/MANGO/draft-0.1/vo-dml/mango.vo-dml.xml",
    )
    mivot_annotations.set_report(True, "Mivot writer unit test")

    mivot_annotations.add_templates(position)
    mivot_annotations.add_globals(space_sys)

    mivot_annotations.build_mivot_block()
    with open(
        os.path.join(data_path, "reference/test_mivot_writer.xml"), "r"
    ) as xml_ref:
        assert strip_xml(xml_ref.read()) == strip_xml(mivot_annotations.mivot_block)

    votable = parse(votable_path)
    mivot_annotations.insert_into_votable(votable)

    mv = MivotViewer(votable)
    assert mv.dm_instance.to_dict() == DictUtils.read_dict_from_file(
        os.path.join(data_path, "reference/test_mivot_writer.json")
    )


@pytest.mark.skipif(not check_astropy_version(), reason="need astropy 6+")
def test_frames():
    """
    Test the generation of both spatial and temporal frames according to the Coords 1.0 model,
    and verify their insertion into the GLOBALS element.
    """
    mivot_annotations = MivotAnnotations()
    mivot_annotations.add_simple_space_frame(ref_frame="FK5",
                                             ref_position="BARYCENTER",
                                             equinox="J2000",
                                             dmid="_fk5"
                                             )
    mivot_annotations.add_simple_time_frame(ref_frame="TCB",
                                            ref_position="BARYCENTER",
                                            dmid="_tcb"
                                            )
    mivot_annotations.build_mivot_block()

    with open(os.path.join(data_path, "reference/test_mivot_frames.xml"),
              "r"
              ) as xml_ref:
        assert strip_xml(xml_ref.read()) == strip_xml(mivot_annotations.mivot_block)

    votable = parse(votable_path)
    mivot_annotations.insert_into_votable(votable)
