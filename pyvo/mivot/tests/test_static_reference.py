# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Test for mivot.features.static_reference_resolver.py
"""
import os
import pytest
from pyvo.mivot.seekers.annotation_seeker import AnnotationSeeker
from pyvo.mivot.features.static_reference_resolver import StaticReferenceResolver
from pyvo.mivot.version_checker import check_astropy_version
from pyvo.mivot import MivotViewer
from . import XMLOutputChecker


@pytest.mark.skipif(not check_astropy_version(), reason="need astropy 6+")
def test_static_reference_resolve(a_seeker, instance, data_path):
    StaticReferenceResolver.resolve(a_seeker, None, instance)
    XMLOutputChecker.assertXmltreeEqualsFile(instance.getroot(),
                                     os.path.join(data_path,
                                                 "data/reference/static_reference_resolved.xml"))


@pytest.fixture
def instance(data_path):
    return XMLOutputChecker.xmltree_from_file(os.path.join(
        data_path,
        "data/static_reference.xml"))


@pytest.fixture
def data_path():
    return os.path.dirname(os.path.realpath(__file__))


@pytest.fixture
def a_seeker(data_path):
    m_viewer = MivotViewer(os.path.join(data_path, "data", "test.mivot_viewer.xml"),
                       tableref="Results")
    return AnnotationSeeker(m_viewer._mapping_block)
