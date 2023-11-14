# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Test for mivot.seekers.annotation_seeker.py
"""
import os
import pytest
from lxml import etree

from pyvo.mivot.utils.xml_utils import XmlUtils
from pyvo.mivot.seekers.annotation_seeker import AnnotationSeeker
from pyvo.mivot.utils.dict_utils import DictUtils
from pyvo.utils import activate_features
activate_features('MIVOT')


@pytest.fixture
def a_seeker(data_path):
    # Creation of an instance of mapping_block, it returns an AnnotationSeeker based on this mapping_block
    mapping_block = XmlUtils.xmltree_from_file(
        os.path.join(data_path, "data/input/test.0.xml"))
    return AnnotationSeeker(mapping_block.getroot())


@pytest.fixture
def data_path():
    return os.path.dirname(os.path.realpath(__file__))


def test_multiple_tableref(data_path):
    mapping_block = XmlUtils.xmltree_from_file(
        os.path.join(data_path, "data/output/test.0.6.xml"))
    with pytest.raises(Exception, match="TEMPLATES without tableref must be unique"):
        AnnotationSeeker(mapping_block.getroot())

def test_all_reverts(a_seeker, data_path):

    # Checks the GLOBALS block given by the AnnotationSeeker by comparing it to the content of the file test.0.1.xml
    XmlUtils.assertXmltreeEqualsFile(a_seeker.globals_block,
                                     os.path.join(data_path, "data/output/test.0.1.xml"))

    # Checks the TEMPLATES block given by the AnnotationSeeker by comparing it to the content of the file test.0.2.xml
    XmlUtils.assertXmltreeEqualsFile(a_seeker.get_templates_block("Results"),
                                     os.path.join(data_path, "data/output/test.0.2.xml"))

    # Checks the list of all the tableref found by the AnnotationSeeker
    assert list(a_seeker.templates_tableref) == ['_PKTable', 'Results']

    # a_seeker should have only 2 COLLECTIONS in GLOBALS: _CoordinateSystems and _Datasets
    assert len(a_seeker.globals_collections) == 2
    # a_seeker should have only 1 INSTANCES in GLOBALS: _tg1
    assert len(a_seeker.get_globals_instances()) == 1

    assert a_seeker.get_globals_instance_dmtypes() == ['ds:experiment.Target']

    assert a_seeker.get_globals_instance_dmids() == ['_timesys', '_spacesys1', '_photsys_G', '_photsys_RP', '_photsys_BP',
                                                    '_ds1', '_tg1', '_TimeSeries', '_ts_data']

    assert a_seeker.get_globals_collection_dmids() == ['_CoordinateSystems', '_Datasets']

    XmlUtils.assertXmltreeEqualsFile(a_seeker.get_globals_instance_by_dmid('_ts_data'),
                                     os.path.join(data_path, "data/output/test.0.3.xml"))

    selection = a_seeker.get_instance_by_dmtype("coords")
    assert len(selection["GLOBALS"]) == 5
    for ele in selection["GLOBALS"]:
        assert ele.get("dmtype").startswith("coords")

    assert len(selection["TEMPLATES"]["_PKTable"]) == 0
    assert len(selection["TEMPLATES"]["Results"]) == 3
    for _, table_sel in selection["TEMPLATES"].items():
        for ele in table_sel:
            assert ele.get("dmtype").startswith("coords")

    with pytest.raises(Exception, match="INSTANCE with PRIMARY_KEY = wrong_key_value in COLLECTION dmid wrong_key_value not found"):
        a_seeker.get_collection_item_by_primarykey("_Datasets", "wrong_key_value")

    pksel = a_seeker.get_collection_item_by_primarykey("_Datasets", "5813181197970338560")
    XmlUtils.assertXmltreeEqualsFile(pksel,
                                     os.path.join(data_path, "data/output/test.0.4.xml"))

    with pytest.raises(Exception, match="More than one INSTANCE with PRIMARY_KEY = G found in COLLECTION dmid G"):
        double_key = etree.fromstring("""<PRIMARY_KEY dmtype="ivoa:string" value="G"/>""")
        a_seeker.get_collection_item_by_primarykey("_CoordinateSystems", "G").append(double_key)
        a_seeker.get_collection_item_by_primarykey("_CoordinateSystems", "G")
    with pytest.raises(Exception, match="INSTANCE with PRIMARY_KEY = wrong_key in COLLECTION dmid wrong_key not found"):
        a_seeker.get_collection_item_by_primarykey("_CoordinateSystems", "wrong_key")



    assert a_seeker.get_instance_dmtypes() == DictUtils.read_dict_from_file(
        os.path.join(data_path, "data/output/test.0.5.json"))

    assert a_seeker.get_templates_instance_by_dmid("Results", "wrong_dmid") is None
    assert a_seeker.get_templates_instance_by_dmid("Results", "_ts_data").get("dmtype") == "cube:NDPoint"

    assert (a_seeker.get_globals_instance_from_collection("_CoordinateSystems", "ICRS").get("dmtype")
            == "coords:SpaceSys")
    assert a_seeker.get_globals_instance_from_collection("wrong_dmid", "ICRS") is None


if __name__ == '__main__':
    pytest.main()
