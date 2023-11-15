# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Test for mivot.viewer.model_viewer_layer3.py
"""
import os
import pytest
from pyvo.mivot.viewer.model_viewer import ModelViewer
from pyvo.mivot.viewer.model_viewer_layer3 import ModelViewerLayer3
from pyvo.utils.prototype import activate_features
activate_features('MIVOT')


def test_dict_model_viewer3(votable_test, simple_votable):
    """
    To test the generation of the MIVOT class, the function builds a ModelViewerLayer3
    with his MIVOT class and his previous dictionary from XML.
    Then, it calls the function recursive_check which recursively compares an element of MIVOT class
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
                    assert (value['value'] in
                            ('notset', 'noset', 'null', 'none', 'NotSet', 'NoSet', 'Null', 'None'))
                else:
                    if value['value'] is not None:
                        assert isinstance(value['value'], str)

                recursive_check(MivotClass.__dict__[MivotClass.remove_model_name(key)], **value)
            else:
                assert key == 'dmtype' or 'value'


@pytest.fixture
def m_viewer(data_path):
    votable = os.path.join(data_path, "data/input/test.1.xml")
    return ModelViewer(votable_path=votable)


@pytest.fixture
def votable_test(data_path):
    votable = os.path.join(data_path, "data/vizier_csc2_gal.annot.xml")
    return votable


@pytest.fixture
def simple_votable(data_path):
    votable = os.path.join(data_path, "data/simple-annotation-votable.xml")
    return votable


@pytest.fixture
def data_path():
    return os.path.dirname(os.path.realpath(__file__))


if __name__ == '__main__':
    pytest.main()
