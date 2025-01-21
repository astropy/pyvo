# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
This module contains test cases for validating the functionality of MivotInstance, MivotAnnotations,
and related components in the pyvo.mivot package. These tests ensure that the classes behave as
expected, including error handling and XML generation for data models.
"""

import os
import pytest
from unittest.mock import patch
from astropy.io.votable import parse
from astropy.utils.data import get_pkg_data_contents, get_pkg_data_filename
from pyvo.utils import activate_features
from pyvo.utils import testing, vocabularies

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

@pytest.fixture()
def mocked_fps_xxx(mocker):
    def callback(request, context):
        return get_pkg_data_contents('data/datalink/datalink.xml')
    print("===================")
    with mocker.register_uri(
        'GET', 'http://svo2.cab.inta-csic.es/svo/theory/fps/fpsmivot.php?PhotCalID=SLOAN/SDSS.g/AB', content=callback
    ) as matcher:
        yield matcher

@pytest.fixture
def mocked_fps():
    with patch('requests.get') as mock_get:
        yield mock_get

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
    dmid = mivot_annotations.add_simple_space_frame(ref_frame="FK5",
                                             ref_position="BARYCENTER",
                                             equinox="J2000"
                                             )
    assert dmid == "_spaceframe_FK5_J2000_BARYCENTER"
    dmid = mivot_annotations.add_simple_time_frame(ref_frame="TCB",
                                            ref_position="BARYCENTER"
                                            )
    assert dmid == "_timeframe_TCB_BARYCENTER"

    mivot_annotations.build_mivot_block(no_schema_check=True)

    with open(os.path.join(data_path, "reference/test_mivot_frames.xml"),
              "r"
              ) as xml_ref:
        assert strip_xml(xml_ref.read()) == strip_xml(mivot_annotations.mivot_block)

    votable = parse(votable_path)
    mivot_annotations.insert_into_votable(votable)

@pytest.mark.skipif(not check_astropy_version(), reason="need astropy 6+")
def test_phot_cal():
     # Mock setup
     
    with patch('requests.get') as mock_get:
        # Configure the mock to return a response with the XML content
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = get_pkg_data_contents('data/test.photcal_error.xml')
        # Call the function
        mivot_annotations = MivotAnnotations()
        assert mivot_annotations.add_photcal("aeaea") == None

        mock_get.return_value.content = get_pkg_data_contents('data/test.photcal_SDSS.xml')
        # Call the function
        mivot_annotations = MivotAnnotations()
        dmid = mivot_annotations.add_photcal("SLOAN/SDSS.g/AB")
        assert dmid == "_photcal_SLOAN_SDSS_g_AB"
        mivot_annotations.build_mivot_block(no_schema_check=True)
        assert (strip_xml(get_pkg_data_contents('data/reference/test_mivot_photcal.xml')) == strip_xml(mivot_annotations.mivot_block))

        mivot_annotations.add_photcal("SLOAN/SDSS.g/AB")
        mivot_annotations.build_mivot_block(no_schema_check=True)
        assert (strip_xml(get_pkg_data_contents('data/reference/test_mivot_photcal.xml')) == strip_xml(mivot_annotations.mivot_block))


if __name__ == "__main__":
    mivot_annotations = MivotAnnotations()
    dmid = mivot_annotations.add_photcal("SLOAN/SDSS.g/AB")


