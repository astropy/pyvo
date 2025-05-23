# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
This module contains test cases for validating the functionality of MivotInstance, MivotAnnotations,
and related components in the pyvo.mivot package. These tests ensure that the classes behave as
expected, including error handling and XML generation for data models.
"""

import os
import pytest
from pyvo.utils import activate_features

from pyvo.mivot.version_checker import check_astropy_version
from pyvo.mivot.utils.exceptions import MappingError
from pyvo.mivot.utils.xml_utils import XmlUtils
from pyvo.mivot.writer.annotations import MivotAnnotations
from pyvo.mivot.writer.instance import MivotInstance

# Enable MIVOT-specific features in the pyvo library
activate_features("MIVOT")

# File paths for test data
votable_path = os.path.realpath(
    os.path.join(__file__, "..", "data", "test.mivot_viewer.no_mivot.xml")
)
data_path = os.path.realpath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")
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
        value="*value1",
        unit="m/s",
    )
    assert XmlUtils.strip_xml(instance1.xml_string()) == (
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
