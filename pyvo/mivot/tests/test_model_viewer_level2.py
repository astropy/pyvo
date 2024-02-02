# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Test for mivot.viewer.model_viewer_level2.py
"""
import os
import pytest
from pyvo.mivot.version_checker import check_astropy_version
from pyvo.mivot.viewer.model_viewer_level1 import ModelViewerLevel1
from pyvo.mivot.viewer.model_viewer_level2 import ModelViewerLevel2
from pyvo.utils.prototype import activate_features


activate_features('MIVOT')


def test_model_viewer_level2(m_viewer):
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")
    m_viewer.get_next_row()
    mv_level1 = ModelViewerLevel2(m_viewer)
    with pytest.raises(Exception, match="Cannot find dmrole wrong_role in any instances of the VOTable"):
        mv_level1.get_instance_by_role("wrong_role")
        mv_level1.get_instance_by_role("wrong_role", all=True)
    with pytest.raises(Exception, match="Cannot find dmtype wrong_dmtype in any instances of the VOTable"):
        mv_level1.get_instance_by_type("wrong_dmtype")
        mv_level1.get_instance_by_type("wrong_dmtype", all=True)
    with pytest.raises(Exception, match="Cannot find dmrole wrong_role in any collections of the VOTable"):
        mv_level1.get_collection_by_role("wrong_role")
        mv_level1.get_collection_by_role("wrong_role", all=True)
    instances_list_role = mv_level1.get_instance_by_role("cube:MeasurementAxis.measure", all=True)
    assert len(instances_list_role) == 3
    instances_list_type = mv_level1.get_instance_by_type("cube:Observable", all=True)
    assert len(instances_list_type) == 3
    collections_list_role = mv_level1.get_collection_by_role("cube:NDPoint.observable", all=True)
    assert len(collections_list_role) == 1


@pytest.fixture
def m_viewer(data_path):
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")
    votable = os.path.join(data_path, "data/input/test.1.xml")
    return ModelViewerLevel1(votable_path=votable, tableref="Results")


@pytest.fixture
def data_path():
    return os.path.dirname(os.path.realpath(__file__))


if __name__ == '__main__':
    pytest.main()
