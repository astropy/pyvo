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

if __name__ == "__main__":
    mivot_annotations = MivotAnnotations()
    mivot_annotations.add_photcal("aeaea")
    mivot_annotations.add_photcal("SLOAN/SDSS.g/AB")
