# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Test for mivot.features.static_reference_resolver.py
"""
import os
import pytest
from urllib.request import urlretrieve
from pyvo.mivot.utils.xml_utils import XmlUtils
from pyvo.mivot.seekers.annotation_seeker import AnnotationSeeker
from pyvo.mivot.features.static_reference_resolver import StaticReferenceResolver
from pyvo.mivot.version_checker import check_astropy_version
from pyvo.utils import activate_features

activate_features('MIVOT')


@pytest.mark.remote_data
def test_static_reference_resolve(a_seeker, instance, data_path):
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")
    StaticReferenceResolver.resolve(a_seeker, None, instance)
    XmlUtils.assertXmltreeEqualsFile(instance.getroot(),
                                     os.path.join(data_path,
                                                 "data/output/static_reference_resolved.xml"))


@pytest.fixture
def instance(data_path):
    return XmlUtils.xmltree_from_file(os.path.join(
        data_path,
        "data/input/static_reference.xml"))


@pytest.fixture
def data_path():
    return os.path.dirname(os.path.realpath(__file__))


@pytest.fixture
def data_sample_url():
    return "https://raw.githubusercontent.com/ivoa/dm-usecases/main/pyvo-ci-sample/"


@pytest.fixture
def a_seeker(data_path, data_sample_url):
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")

    votable_name = "test.0.xml"
    votable_path = os.path.join(data_path, "data", "input", votable_name)
    urlretrieve(data_sample_url + votable_name,
                votable_path)
    mapping_block = XmlUtils.xmltree_from_file(votable_path)
    yield AnnotationSeeker(mapping_block.getroot())
    os.remove(votable_path)


if __name__ == '__main__':
    pytest.main()
