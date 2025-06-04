#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.io.uws
"""

import pytest
import pyvo.io.uws as uws
from pyvo.io.uws.tree import ExtensibleUWSElement

from astropy.utils.data import get_pkg_data_filename


class TestJob:
    def test_job(self):
        job = uws.parse_job(get_pkg_data_filename(
            "data/job.xml"))

        assert job.jobid == '1337'
        assert job.version == '1.1'

        job = uws.parse_job(get_pkg_data_filename(
            "data/job-implicit-v1.0.xml"))

        assert job.version == '1.0'

    def test_error_job(self):
        job = uws.parse_job(get_pkg_data_filename(
            "data/job-error.xml"))

        assert job.jobid == '1337'
        assert job.version == '1.1'

        assert not job.errorsummary.has_detail
        assert job.errorsummary.type_ == 'fatal'
        assert job.errorsummary.message.content == 'We have problem'

    def test_simple_jobinfo(self):
        job = uws.parse_job(get_pkg_data_filename(
            "data/job-with-simple-jobinfo.xml"))

        assert job.jobinfo is not None

        assert 'tapQueryInfo' in job.jobinfo
        assert job.jobinfo['tapQueryInfo'] is not None

        tap_info = job.jobinfo['tapQueryInfo']
        assert 'pct_complete' in tap_info
        assert 'chunks_processed' in tap_info
        assert 'total_chunks' in tap_info

        assert tap_info['pct_complete'].value == 100
        assert tap_info['chunks_processed'].value == 1
        assert tap_info['total_chunks'].value == 1
        assert tap_info['pct_complete'].text == "100"

        keys = list(job.jobinfo.keys())
        assert 'tapQueryInfo' in keys

    def test_jobinfo_multiple_access_patterns(self):
        job = uws.parse_job(get_pkg_data_filename(
            "data/job-with-simple-jobinfo.xml"))

        assert job.jobinfo is not None

        tap_info1 = job.jobinfo['tapQueryInfo']
        tap_info2 = job.jobinfo.get('tapQueryInfo')

        assert tap_info1 is tap_info2
        assert tap_info1 is not None

    def test_jobinfo_text_content_and_types(self):
        job = uws.parse_job(get_pkg_data_filename(
            "data/job-with-typed-jobinfo.xml"))

        assert job.jobinfo is not None

        int_elem = job.jobinfo['integer_value']
        assert int_elem.value == 100
        assert isinstance(int_elem.value, int)
        assert int_elem.text == "100"

        float_elem = job.jobinfo['float_value']
        assert float_elem.value == 3.14
        assert isinstance(float_elem.value, float)
        assert float_elem.text == "3.14"

        string_elem = job.jobinfo['string_value']
        assert string_elem.value == "pyvo"
        assert isinstance(string_elem.value, str)
        assert string_elem.text == "pyvo"

        empty_elem = job.jobinfo['empty_value']
        assert empty_elem.value is None
        assert empty_elem.text is None

    def test_jobinfo_get_methods(self):
        job = uws.parse_job(get_pkg_data_filename(
            "data/job-with-simple-jobinfo.xml"))

        jobinfo = job.jobinfo

        assert jobinfo.get('nonexistent') is None
        assert jobinfo.get('nonexistent', 'default') == 'default'

        tap_info = jobinfo.get('tapQueryInfo')
        assert tap_info is not None
        assert 'tapQueryInfo' in jobinfo
        assert 'nonexistent' not in jobinfo

        tap_info = jobinfo['tapQueryInfo']
        assert tap_info is not None

        with pytest.raises(KeyError):
            _ = jobinfo['nonexistent']

    def test_jobinfo_edge_cases(self):
        job = uws.parse_job(get_pkg_data_filename(
            "data/job-with-simple-jobinfo.xml"))

        jobinfo = job.jobinfo

        str_repr = str(jobinfo)
        assert 'jobInfo' in str_repr or len(str_repr) > 0

        repr_str = repr(jobinfo)
        assert 'ExtensibleUWSElement' in repr_str
        assert 'elements=' in repr_str

    def test_no_jobinfo(self):
        job = uws.parse_job(get_pkg_data_filename(
            "data/job.xml"))

        assert job.jobinfo is None

    def test_nested_jobinfo_access(self):
        job = uws.parse_job(get_pkg_data_filename(
            "data/job-with-nested-jobinfo.xml"))

        assert job.jobinfo is not None

        query_info = job.jobinfo['queryInfo']
        assert query_info is not None

        metrics = query_info['metrics']
        assert metrics is not None
        assert metrics['execution_time'].value == 1500
        assert metrics['rows_returned'].value == 100

    def test_jobinfo_overwrite_behavior(self):
        job = uws.parse_job(get_pkg_data_filename(
            "data/job-with-duplicate-elements.xml"))

        assert job.jobinfo is not None

        status = job.jobinfo.get('status')
        assert status is not None
        assert status.value == "completed"

    def test_extensible_element_creation(self):
        element = ExtensibleUWSElement(config={}, pos=(1, 1), _name='test')
        assert element._name == 'test'
        assert len(element._elements) == 0

        assert 'test' in str(element)
        assert 'elements=0' in repr(element)

        assert 'nonexistent' not in element
        assert element.get('nonexistent') is None
        assert list(element.keys()) == []

    def test_jobinfo_namespace_elements(self):
        job = uws.parse_job(get_pkg_data_filename(
            "data/job-with-namespace-elements.xml"))

        assert job.jobinfo is not None

        progress = job.jobinfo.get('progress')
        assert progress is not None
        # Assert that the value is the last one of the elements with the same name
        assert progress.value == 75

        unique_elem = job.jobinfo.get('uniqueElement')
        assert unique_elem is not None

        keys = job.jobinfo.keys()
        assert len(keys) > 0

    def test_multiple_elements_same_name(self):
        job = uws.parse_job(get_pkg_data_filename(
            "data/job-with-duplicate-elements.xml"))

        assert job.jobinfo is not None

        _ = [key for key in job.jobinfo.keys() if 'status' in key]

        status = job.jobinfo['status']
        assert status.value == "completed"

    def test_empty_jobinfo(self):
        job = uws.parse_job(get_pkg_data_filename(
            "data/job-with-empty-jobinfo.xml"))

        assert job.jobinfo is not None
        assert len(job.jobinfo.keys()) == 0
        assert len(job.jobinfo._elements) == 0

    def test_jobinfo_numeric_content_conversion(self):
        element = ExtensibleUWSElement(config={}, pos=(1, 1), _name='test')
        element.content = 100
        assert not isinstance(element.content, str)
        assert element.content == 100
        element.parse(iter([]), {})
        assert element.text == "100"
        assert element.value == 100
        assert isinstance(element.text, str)
