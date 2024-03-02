# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Test for mivot.viewer.model_viewer_level1.py
"""
import os
import pytest
import re
from urllib.request import urlretrieve
from pyvo.mivot.utils.vocabulary import Constant
from pyvo.mivot.utils.dict_utils import DictUtils
from pyvo.mivot.utils.exceptions import MappingException
from pyvo.mivot.version_checker import check_astropy_version
from pyvo.mivot.viewer.mivot_viewer import MivotViewer
from pyvo.utils.prototype import activate_features
from astropy import version as astropy_version


activate_features('MIVOT')


@pytest.mark.remote_data
def test_model_viewer_level1_constructor(path_to_test_1):
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")
    with (pytest.raises(TypeError, match="'<' not supported between instances of 'str' and 'int'")
          and pytest.raises(Exception, match="Resource #1 is not found")):
        MivotViewer(path_to_test_1, resource_number=1)


@pytest.mark.remote_data
def test_first_instance_row_view(path_to_first_instance):
    """
    Test the function get_first_instance_dmtype() which is
    used to find the first INSTANCE/COLLECTION in TEMPLATES.
    """
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")

    m_viewer = MivotViewer(votable_path=path_to_first_instance)
    assert m_viewer.get_first_instance_dmtype("one_instance") == "one_instance"
    assert m_viewer.get_first_instance_dmtype("coll_and_instances") == "first"
    assert m_viewer.get_first_instance_dmtype("one_collection") == Constant.ROOT_COLLECTION
    assert m_viewer.get_first_instance_dmtype("only_collection") == Constant.ROOT_COLLECTION
    with pytest.raises(Exception, match="Can't find the first INSTANCE/COLLECTION in TEMPLATES"):
        m_viewer.get_first_instance_dmtype("empty")


@pytest.mark.remote_data
def test_table_ref(m_viewer):
    """
    Test if the model_viewer_level1 can find each table_ref and connect to the right table_ref.
    Test if the model_viewer_level1 can find each models.
    """
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


@pytest.mark.remote_data
def test_global_getters(m_viewer, data_path):
    """
    Test each getter of the model_viewer_level1 specific for the GLOBALS.
    """
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")
    assert m_viewer.get_table_ids() == ['_PKTable', 'Results']
    assert m_viewer.get_globals_models() == DictUtils.read_dict_from_file(
        os.path.join(data_path, "data/output/globals_models.json"))
    assert m_viewer.get_templates_models() == DictUtils.read_dict_from_file(
        os.path.join(data_path, "data/output/templates_models.json"))
    m_viewer._connect_table('_PKTable')
    row = m_viewer.next_table_row()
    assert row[0] == '5813181197970338560'
    assert row[1] == 'G'
    row = m_viewer.next_table_row()
    assert row[0] == '5813181197970338560'
    assert row[1] == 'BP'
    m_viewer.rewind()
    row = m_viewer.next_table_row()
    assert row[0] == '5813181197970338560'
    assert row[1] == 'G'


@pytest.mark.remote_data
def test_no_mivot(path_no_mivot):
    """
    Test each getter of the model_viewer_level1 specific for the GLOBALS.
    """
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")
    m_viewer = MivotViewer(path_no_mivot)
    assert m_viewer.get_table_ids() is None
    assert m_viewer.get_globals_models() is None

    assert m_viewer.get_templates_models() is None
    with pytest.raises(MappingException):
        m_viewer._connect_table('_PKTable')
    with pytest.raises(MappingException):
        m_viewer._connect_table()

    assert m_viewer.next_table_row() is None


@pytest.mark.remote_data
def test_check_version(path_to_test_1):
    if check_astropy_version() is False:
        with pytest.raises(Exception,
                           match=f"Astropy version {astropy_version.version} "
                                 f"is below the required version 6.0 for the use of MIVOT."):
            MivotViewer(votable_path=path_to_test_1)
    if astropy_version.version is None:
        assert check_astropy_version() is False
    elif astropy_version.version < '6.0':
        assert check_astropy_version() is False
    else:
        assert check_astropy_version() is True


@pytest.fixture
def m_viewer(data_path, data_sample_url):
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")

    votable_name = "test.1.xml"
    votable_path = os.path.join(data_path, "data", "input", votable_name)
    urlretrieve(data_sample_url + votable_name,
                votable_path)

    yield MivotViewer(votable_path=votable_path)
    os.remove(votable_path)


@pytest.fixture
def path_to_test_1(data_path, data_sample_url):
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")

    votable_name = "test.1.xml"
    votable_path = os.path.join(data_path, "data", "input", votable_name)
    urlretrieve(data_sample_url + votable_name,
                votable_path)

    yield votable_path
    os.remove(votable_path)


@pytest.fixture
def path_to_first_instance(data_path, data_sample_url):
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")

    votable_name = "test_first_instance.xml"
    votable_path = os.path.join(data_path, "data", votable_name)
    urlretrieve(data_sample_url + votable_name,
                votable_path)

    yield votable_path
    os.remove(votable_path)


@pytest.fixture
def path_no_mivot(data_path, data_sample_url):
    votable_name = "vizier_no_mivot.xml"
    votable_path = os.path.join(data_path, "data", votable_name)
    urlretrieve(data_sample_url + votable_name,
                votable_path)

    yield votable_path
    os.remove(votable_path)


@pytest.fixture
def data_path():
    return os.path.dirname(os.path.realpath(__file__))


@pytest.fixture
def data_sample_url():
    return "https://raw.githubusercontent.com/ivoa/dm-usecases/main/pyvo-ci-sample/"


@pytest.fixture
def vizier_url():
    return "https://cdsarc.cds.unistra.fr/beta/viz-bin/mivotconesearch/I/239/hip_main"


if __name__ == '__main__':
    pytest.main()