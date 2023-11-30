# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Test for mivot.viewer.model_viewer_layer3.py
"""
import os
import pytest

from pyvo.mivot.utils.xml_utils import XmlUtils
from pyvo.mivot.version_checker import check_astropy_version
from pyvo.mivot.viewer.model_viewer import ModelViewer
from pyvo.utils.prototype import activate_features
activate_features('MIVOT')


def test_model_viewer3(votable_test, simple_votable):
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")

    m_viewer_votable_test = ModelViewer(votable_path=votable_test)
    m_viewer_votable_test.get_next_row_view()
    mv_niv1_votable_test = m_viewer_votable_test._model_viewer_layer1
    mv_niv3_votable_test = m_viewer_votable_test._model_viewer_layer3
    MivotClass = mv_niv3_votable_test.mivot_class

    xml_simple_votable = mv_niv1_votable_test._xml_view
    assert xml_simple_votable.tag == 'TEMPLATES'
    XmlUtils.pretty_print(xml_simple_votable)

    recusive_xml_check(xml_simple_votable, MivotClass)

def recusive_xml_check(xml_simple_votable, MivotClass):
    print("=======================================")
    if xml_simple_votable.tag == 'TEMPLATES':
        recusive_xml_check(xml_simple_votable[0], MivotClass)
    else:
        for child in xml_simple_votable:
            if child.tag == 'INSTANCE':
                print("INSTANCE : ", child.tag, " : ", child.attrib, " | MivotClass : ", MivotClass.__dict__)
                for key, value in child.attrib.items():
                    if key == 'dmrole':

                        if value == '':
                            if child.tag == 'ATTRIBUTE':
                                print(value, child.get('dmrole'))
                                recusive_xml_check(child,
                                               getattr(MivotClass, MivotClass._remove_model_name(child.get('dmrole'))))
                            elif child.tag == 'INSTANCE':
                                print(value, child.get('dmrole'))
                                print("        INSTANCE : ", child.tag, " : ", child.attrib, " | MivotClass : ",
                                      MivotClass.__dict__)
                                recusive_xml_check(child, getattr(MivotClass,
                                                                  MivotClass._remove_model_name(child.get('dmrole'), True)))
                                print(key, value)
                            # for child2 in child:
                            #     if child2.tag == 'ATTRIBUTE':
                            #         recusive_xml_check(child, getattr(MivotClass, MivotClass._remove_model_name(child2.get('dmrole'))))
                            #     elif child2.tag == 'INSTANCE':
                            #         print(value, child2.get('dmrole'))
                            #         print("        INSTANCE : ", child2.tag, " : ", child2.attrib, " | MivotClass : ", MivotClass.__dict__)
                            #         recusive_xml_check(child, getattr(MivotClass, MivotClass._remove_model_name(child2.get('dmrole'), True)))
                        else:
                            if child.tag == 'ATTRIBUTE':
                                recusive_xml_check(child, getattr(MivotClass, MivotClass._remove_model_name(child.get('dmrole'))))
                            elif child.tag == 'INSTANCE':
                                recusive_xml_check(child, getattr(MivotClass, MivotClass._remove_model_name(child.get('dmrole'), True)))



                        # for child2 in child:
                        #     print("-------------------")
                        #     print("child ",child2.tag, " : ", child2.attrib, " | MivotClass : ", MivotClass.__dict__)
                        #     for key2, value2 in child2.attrib.items():
                        #         if key2 == 'dmrole':
                        #             if child2.tag == 'ATTRIBUTE':
                        #                 print(child2.tag, child2.attrib)
                        #                 print(key2, value2)
                        #                 print(MivotClass.__dict__)
                        #                 if value != '':
                        #                     print("@@@@@@@@@@",getattr(MivotClass, MivotClass._remove_model_name(value)).__dict__)
                        #                     next_mivot_class = getattr(MivotClass, MivotClass._remove_model_name(value))
                        #                     recusive_xml_check(child2, getattr(next_mivot_class, MivotClass._remove_model_name(value2)))
                        #                 else:
                        #                     recusive_xml_check(child2, getattr(MivotClass, MivotClass._remove_model_name(value2)))
                        #             if child2.tag == 'INSTANCE':
                        #
                        #                 print("======", getattr(MivotClass, MivotClass._remove_model_name(value2,True)).__dict__)
                        #                 print("la value de dmrole : ", value)
                        #                 if value != '':
                        #                     print("@@@@@@@@@@", getattr(MivotClass, MivotClass._remove_model_name(value, True)).__dict__)
                        #                     next_mivot_class = getattr(MivotClass, MivotClass._remove_model_name(value, True))
                        #                     recusive_xml_check(child2, getattr(next_mivot_class, MivotClass._remove_model_name(value2, True)))
                        #                 else:
                        #                     recusive_xml_check(child2, getattr(MivotClass, MivotClass._remove_model_name(value2, True)))
                                    # else:
                                    #     print(key2, value2)
                    # elif key == 'dmtype':
                    #     print(value)
                    #     print(MivotClass._remove_model_name(value, False))
                    #     assert MivotClass._remove_model_name(value, False) == MivotClass.dmtype

            elif child.tag == 'COLLECTION':

                for key, value in child.attrib.items():
                    print("COLLECTION : ", key, value)
                    if key == 'dmtype':
                        assert value == MivotClass.dmtype
                        for child2 in child:
                            print(child2.tag, child2.attrib)
                            recusive_xml_check(child2, MivotClass)
                    elif key == 'ref':
                        assert value == MivotClass.ref
                    elif key == 'unit':
                        assert value == MivotClass.unit
                    elif key == 'value':
                        assert value == MivotClass.value

                for child2 in child:
                    recusive_xml_check(child2, MivotClass)
            elif child.tag == 'ATTRIBUTE':
                print("ATTRIBUTE : ", child.tag, child.attrib, " |  MivotClass : ", MivotClass.__dict__)
                for key, value in child.attrib.items():
                    if key == 'dmtype':
                        assert MivotClass.dmtype in value
                    # elif key == 'ref':
                    #     assert value == MivotClass.ref
                    # elif key == 'unit':
                    #     assert value == MivotClass.unit
                    # elif key == 'value':
                    #     assert value == MivotClass.value
                    # else:
                    #     key in ('col_index', 'field_unit')
            else:
                assert False

    # for key, value in xml_simple_votable.attrib.items():
    #     print(xml_simple_votable.tag, key, value)



def test_dict_model_viewer3(votable_test, simple_votable):
    """
    To test the generation of the MIVOT class, the function builds a ModelViewerLayer3
    with his MIVOT class and his previous dictionary from XML.
    Then, it calls the function recursive_check which recursively compares an element of MIVOT class
    with the dictionary on which it was built.
    MIVOT class is itself a dictionary with only essential information of the ModelViewerLayer3._dict.
    This test run on 2 votables : votable_test and simple_votable.
    """
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")
    m_viewer_votable_test = ModelViewer(votable_path=votable_test)
    m_viewer_votable_test.get_next_row_view()
    m_viewer3 = m_viewer_votable_test._model_viewer_layer3
    recursive_check(m_viewer3.mivot_class, **m_viewer3._dict)

    m_viewer_simple_votable = ModelViewer(votable_path=simple_votable)
    m_viewer_simple_votable.get_next_row_view()
    mv_niv3 = m_viewer_simple_votable._model_viewer_layer3
    recursive_check(mv_niv3.mivot_class, **mv_niv3._dict)


def recursive_check(MivotClass, **kwargs):
    for key, value in kwargs.items():
        print(key, value)
        if isinstance(value, list):
            nbr_item = 0
            for item in value:
                if isinstance(item, dict):
                    assert 'dmtype' in item.keys()
                    recursive_check(getattr(MivotClass, MivotClass._remove_model_name(key))[nbr_item], **item)
                    nbr_item += 1

        elif isinstance(value, dict) and 'value' not in value:
            # for INSTANCE of INSTANCEs dmrole needs model_name
            assert MivotClass._remove_model_name(key, True) in vars(MivotClass).keys()
            recursive_check(getattr(MivotClass, MivotClass._remove_model_name(key, True)), **value)

        else:
            if isinstance(value, dict) and MivotClass._is_leaf(**value):
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
                recursive_check(getattr(MivotClass, MivotClass._remove_model_name(key)), **value)
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
