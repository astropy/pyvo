import os
import pytest
import re
from pyvo.mivot.utils.constant import Constant
from pyvo.mivot.utils.dict_utils import DictUtils
from pyvo.mivot.utils.xml_utils import XmlUtils
from pyvo.mivot.viewer.model_viewer import ModelViewer
from pyvo.mivot.viewer.model_viewer_layer3 import ModelViewerLayer3
from pyvo.utils.prototype import activate_features
activate_features('MIVOT')


def test_model_viewer_layer1(m_viewer):
    m_viewer.connect_table("Results")
    m_viewer.get_next_row()
    mv_layer1 = m_viewer.get_model_view_layer1()
    with pytest.raises(Exception, match="Cannot find dmrole wrong_role in any instances of the VOTable"):
        mv_layer1.get_instance_by_role("wrong_role")
        mv_layer1.get_instance_by_role("wrong_role", all=True)
    with pytest.raises(Exception, match="Cannot find dmtype wrong_dmtype in any instances of the VOTable"):
        mv_layer1.get_instance_by_type("wrong_dmtype")
        mv_layer1.get_instance_by_type("wrong_dmtype", all=True)
    with pytest.raises(Exception, match="Cannot find dmrole wrong_role in any collections of the VOTable"):
        mv_layer1.get_collection_by_role("wrong_role")
        mv_layer1.get_collection_by_role("wrong_role", all=True)

    instances_list_role = mv_layer1.get_instance_by_role("cube:MeasurementAxis.measure", all=True)
    assert len(instances_list_role) == 3
    instances_list_type = mv_layer1.get_instance_by_type("cube:Observable", all=True)
    assert len(instances_list_type) == 3
    collections_list_role = mv_layer1.get_collection_by_role("cube:NDPoint.observable", all=True)
    assert len(collections_list_role) == 1


def test_model_viewer_constructor(data_path):
    votable = os.path.join(data_path, "data/input/test.1.xml")

    with (pytest.raises(TypeError, match="'<' not supported between instances of 'str' and 'int'")
          and pytest.raises(Exception, match="Resource #1 is not found")):
        ModelViewer(votable, resource_number=1)


def test_first_instance_row_view(data_path):
    votable = os.path.join(data_path, "data/test_first_instance.xml")
    m_viewer = ModelViewer(votable_path=votable)
    m_viewer.get_next_row()
    assert m_viewer.get_first_instance("one_instance") == "one_instance"
    assert m_viewer.get_first_instance("coll_and_instances") == "first"
    assert m_viewer.get_first_instance("one_collection") == "RootCollection"
    assert m_viewer.get_first_instance("only_collection") == "RootCollection"
    with pytest.raises(Exception, match="Can't find the first INSTANCE/COLLECTION in TEMPLATES"):
        m_viewer.get_first_instance("empty")

    assert m_viewer.get_next_row_view() is not None
    assert m_viewer.get_next_row_view() is None


def test_model_viewer_table_ref(data_path, m_viewer):
    assert m_viewer._mapped_tables == ['_PKTable', 'Results']
    with pytest.raises(Exception, match=re.escape(r"The table first_table doesn't match with any "
                                                  r"mapped_table (['_PKTable', 'Results']) encountered in TEMPLATES")):
        m_viewer.connect_table("wrong_tableref")

    assert m_viewer.connected_table_ref == Constant.FIRST_TABLE
    assert m_viewer.get_models() == {'mango': 'file:/Users/sao/Documents/IVOA/GitHub/ivoa-dm-examples/tmp/Mango-v1.0.vo-dml.xml', 'cube': 'https://volute.g-vo.org/svn/trunk/projects/dm/Cube/vo-dml/Cube-1.0.vo-dml.xml', 'ds': 'https://volute.g-vo.org/svn/trunk/projects/dm/DatasetMetadata/vo-dml/DatasetMetadata-1.0.vo-dml.xml', 'meas': 'https://www.ivoa.net/xml/Meas/20200908/Meas-v1.0.vo-dml.xml', 'coords': 'https://www.ivoa.net/xml/STC/20200908/Coords-v1.0.vo-dml.xml', 'ivoa': 'https://www.ivoa.net/xml/VODML/IVOA-v1.vo-dml.xml'}


def test_model_viewer_global_getters(m_viewer, data_path):
    max_diff = None
    assert m_viewer.get_table_ids() == ['_PKTable', 'Results']

    assert m_viewer.get_globals_models() == DictUtils.read_dict_from_file(
        os.path.join(data_path, "data/output/test.1.11.json"))

    assert m_viewer.get_templates_models() == DictUtils.read_dict_from_file(
        os.path.join(data_path, "data/output/test.1.12.json"))

    m_viewer.connect_table('_PKTable')
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

    XmlUtils.assertXmltreeEqualsFile(m_viewer._templates,
                                     os.path.join(data_path, "data/output/test.1.3.xml"))
    XmlUtils.assertXmltreeEqualsFile(m_viewer._dyn_references["REFERENCE_2"],
                                     os.path.join(data_path, "data/output/test.1.4.xml"))
    XmlUtils.assertXmltreeEqualsFile(m_viewer._joins["JOIN_6"],
                                     os.path.join(data_path, "data/output/test.1.5.xml"))
    model_view = m_viewer._get_model_view()
    XmlUtils.pretty_print(model_view)


def test_dict_model_viewer3(votable_test, simple_votable):
    """
    To test the generation of the MIVOT class, the function build a ModelViewerLayer3
    with his MIVOT class and his previous dictionary from XML.
    Then, it calls the function recursive_check which recursively compare an element of MIVOT class
    with the dictionary on which it was built.
    MIVOT class is itself a dictionary with only essential information of the ModelViewerLayer3._dict.
    This test run on 2 votables : votable_test and simple_votable.
    """
    m_viewer_votable_test = ModelViewer(votable_path=votable_test)
    m_viewer_votable_test.connect_table()
    m_viewer_votable_test.get_next_row()
    mv_niv1_votable_test = m_viewer_votable_test.get_model_view_layer1()
    instance = mv_niv1_votable_test.get_instance_by_type(m_viewer_votable_test.get_first_instance())
    mv_niv3_votable_test = ModelViewerLayer3(instance)
    MivotClass = m_viewer_votable_test.get_next_row_view()
    recursive_check(MivotClass, **mv_niv3_votable_test._dict)

    m_viewer_simple_votable = ModelViewer(votable_path=simple_votable)
    m_viewer_simple_votable .connect_table()
    m_viewer_simple_votable .get_next_row()
    mv_niv1 = m_viewer_simple_votable .get_model_view_layer1()
    instance = mv_niv1.get_instance_by_type(m_viewer_simple_votable.get_first_instance())
    mv_niv3 = ModelViewerLayer3(instance)
    MivotClass = m_viewer_simple_votable .get_next_row_view()
    recursive_check(MivotClass, **mv_niv3._dict)


def recursive_check(MivotClass, **kwargs):
    for key, value in kwargs.items():
        if isinstance(value, list):
            nbr_item = 0
            for item in value:
                if isinstance(item, dict):
                    assert 'dmtype' in item.keys()
                    recursive_check(MivotClass.__dict__[MivotClass.remove_model_name(key)][nbr_item], **item)
                    nbr_item += 1

        elif isinstance(value, dict) and 'value' not in value:
            # for INSTANCE of INSTANCEs dmrole needs model_name
            assert MivotClass.remove_model_name(key, True) in MivotClass.__dict__.keys()
            recursive_check(MivotClass.__dict__[MivotClass.remove_model_name(key, True)], **value)

        else:
            if isinstance(value, dict) and MivotClass.is_leaf(**value):
                assert value.keys().__contains__('dmtype' and 'value' and 'unit' and 'ref')
                lower_dmtype = value['dmtype'].lower()
                if "real" in lower_dmtype or "double" in lower_dmtype or "float" in lower_dmtype:
                    assert isinstance(value['value'], float)
                elif "bool" in lower_dmtype:
                    assert isinstance(value['value'], bool)
                elif value['dmtype'] is None:
                    assert value['value'] in ('notset', 'noset', 'null', 'none', 'NotSet', 'NoSet', 'Null', 'None')
                else:
                    if value['value'] is not None:
                        assert isinstance(value['value'], str)

                recursive_check(MivotClass.__dict__[MivotClass.remove_model_name(key)], **value)
            else:
                assert key == 'dmtype' or 'value'


@pytest.fixture
def data_path():
    return os.path.dirname(os.path.realpath(__file__))


if __name__ == '__main__':
    pytest.main()
