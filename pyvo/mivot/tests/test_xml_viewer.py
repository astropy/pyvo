# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Test for mivot.viewer.model_viewer_level2.py
"""
import os
import pytest
try:
    from defusedxml.ElementTree import Element as element
except ImportError:
    from xml.etree.ElementTree import Element as element
from pyvo.mivot.version_checker import check_astropy_version
from pyvo.mivot.viewer.mivot_viewer import MivotViewer
from pyvo.utils.prototype import activate_features


activate_features('MIVOT')


def test_xml_viewer(m_viewer):
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")
    m_viewer.next()
    xml_viewer = m_viewer.xml_viewer
    with pytest.raises(Exception, match="Cannot find dmrole wrong_role in any instances of the VOTable"):
        xml_viewer.get_instance_by_role("wrong_role")

    with pytest.raises(Exception, match="Cannot find dmrole wrong_role in any instances of the VOTable"):
        xml_viewer.get_instance_by_role("wrong_role", all_instances=True)

    with pytest.raises(Exception, match="Cannot find dmtype wrong_dmtype in any instances of the VOTable"):
        xml_viewer.get_instance_by_type("wrong_dmtype")

    with pytest.raises(Exception, match="Cannot find dmtype wrong_dmtype in any instances of the VOTable"):
        xml_viewer.get_instance_by_type("wrong_dmtype", all_instances=True)

    with pytest.raises(Exception, match="Cannot find dmrole wrong_role in any collections of the VOTable"):
        xml_viewer.get_collection_by_role("wrong_role")

    with pytest.raises(Exception, match="Cannot find dmrole wrong_role in any collections of the VOTable"):
        xml_viewer.get_collection_by_role("wrong_role", all_instances=True)

    instances_list_role = xml_viewer.get_instance_by_role("cube:MeasurementAxis.measure")
    assert isinstance(instances_list_role, element)

    instances_list_role = xml_viewer.get_instance_by_role("cube:MeasurementAxis.measure", all_instances=True)
    assert len(instances_list_role) == 3

    instances_list_type = xml_viewer.get_instance_by_type("cube:Observable")
    assert isinstance(instances_list_type, element)

    instances_list_type = xml_viewer.get_instance_by_type("cube:Observable", all_instances=True)
    assert len(instances_list_type) == 3

    collections_list_role = xml_viewer.get_collection_by_role("cube:NDPoint.observable")
    assert isinstance(collections_list_role, element)

    collections_list_role = xml_viewer.get_collection_by_role("cube:NDPoint.observable", all_instances=True)
    assert len(collections_list_role) == 1


@pytest.fixture
def m_viewer(data_path):
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")

    return MivotViewer(os.path.join(data_path, "data", "test.mivot_viewer.xml"),
                       tableref="Results")


@pytest.fixture
def data_path():
    return os.path.dirname(os.path.realpath(__file__))


if __name__ == '__main__':
    pytest.main()
