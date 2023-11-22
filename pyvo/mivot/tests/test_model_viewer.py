# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Test for mivot.viewer.model_viewer.py
"""
import os
import pytest
import re
from pyvo.mivot.utils.constant import Constant
from pyvo.mivot.utils.dict_utils import DictUtils
from pyvo.mivot.version_checker import check_astropy_version
from pyvo.mivot.viewer.model_viewer import ModelViewer
from pyvo.utils.prototype import activate_features
from astropy import version as astropy_version
activate_features('MIVOT')


def test_model_viewer_constructor(data_path):
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")
    votable = os.path.join(data_path, "data/input/test.1.xml")

    with (pytest.raises(TypeError, match="'<' not supported between instances of 'str' and 'int'")
          and pytest.raises(Exception, match="Resource #1 is not found")):
        ModelViewer(votable, resource_number=1)


def test_first_instance_row_view(data_path):
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")
    votable = os.path.join(data_path, "data/test_first_instance.xml")
    m_viewer = ModelViewer(votable_path=votable)
    m_viewer.get_next_row()
    assert m_viewer.get_first_instance("one_instance") == "one_instance"
    assert m_viewer.get_first_instance("coll_and_instances") == "first"
    assert m_viewer.get_first_instance("one_collection") == Constant.ROOT_COLLECTION
    assert m_viewer.get_first_instance("only_collection") == Constant.ROOT_COLLECTION
    with pytest.raises(Exception, match="Can't find the first INSTANCE/COLLECTION in TEMPLATES"):
        m_viewer.get_first_instance("empty")

    assert m_viewer.get_next_row_view() is not None
    assert m_viewer.get_next_row_view() is None


def test_model_viewer_table_ref(m_viewer):
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")
    assert m_viewer._mapped_tables == ['_PKTable', 'Results']
    with pytest.raises(Exception,
                       match=re.escape(r"The table first_table doesn't match with any mapped_table "
                                       r"(['_PKTable', 'Results']) encountered in TEMPLATES")):
        m_viewer._connect_table("wrong_tableref")

    assert m_viewer.connected_table_ref == Constant.FIRST_TABLE
    assert (m_viewer.get_models()
            == {'mango': 'file:/Users/sao/Documents/IVOA/GitHub/ivoa-dm-examples/tmp/Mango-v1.0.vo-dml.xml',
                'cube': 'https://volute.g-vo.org/svn/trunk/projects/dm/Cube/vo-dml/Cube-1.0.vo-dml.xml',
                'ds': 'https://volute.g-vo.org/svn/trunk/projects/dm/'
                      'DatasetMetadata/vo-dml/DatasetMetadata-1.0.vo-dml.xml',
                'meas': 'https://www.ivoa.net/xml/Meas/20200908/Meas-v1.0.vo-dml.xml',
                'coords': 'https://www.ivoa.net/xml/STC/20200908/Coords-v1.0.vo-dml.xml',
                'ivoa': 'https://www.ivoa.net/xml/VODML/IVOA-v1.vo-dml.xml'})


def test_model_viewer_global_getters(m_viewer, data_path):
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")
    assert m_viewer.get_table_ids() == ['_PKTable', 'Results']

    assert m_viewer.get_globals_models() == DictUtils.read_dict_from_file(
        os.path.join(data_path, "data/output/test_globals_models.json"))

    assert m_viewer.get_templates_models() == DictUtils.read_dict_from_file(
        os.path.join(data_path, "data/output/test_templates_models.json"))

    m_viewer._connect_table('_PKTable')
    row = m_viewer.get_next_row()
    assert row[0] == '5813181197970338560'
    assert row[1] == 'G'

    row = m_viewer.get_next_row()
    assert row[0] == '5813181197970338560'
    assert row[1] == 'BP'

    m_viewer.rewind()
    row = m_viewer.get_next_row()
    assert row[0] == '5813181197970338560'
    assert row[1] == 'G'


def test_check_version(data_path):
    votable = os.path.join(data_path, "data/input/test.1.xml")
    if not check_astropy_version():
        with pytest.raises(Exception,
                           match=f"Astropy version {astropy_version.version} "
                                 f"is below the required version 6.0 for the use of MIVOT."):
            ModelViewer(votable_path=votable)
    if astropy_version.version is None:
        assert check_astropy_version() is False
    elif astropy_version.version < '6.0':
        assert check_astropy_version() is False
    else:
        assert check_astropy_version() is True


@pytest.fixture
def data_path():
    return os.path.dirname(os.path.realpath(__file__))


if __name__ == '__main__':
    pytest.main()
