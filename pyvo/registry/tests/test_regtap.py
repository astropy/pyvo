#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.dal.query
"""
from functools import partial
from urllib.parse import parse_qsl
import pytest

from pyvo.registry import search as regsearch

from astropy.utils.data import get_pkg_data_contents


get_pkg_data_contents = partial(
    get_pkg_data_contents, package=__package__, encoding='binary')


@pytest.fixture()
def capabilities(mocker):
    def callback(request, context):
        return get_pkg_data_contents('data/capabilities.xml')

    with mocker.register_uri(
        'GET', 'http://dc.g-vo.org/tap/capabilities', content=callback
    ) as matcher:
        yield matcher


@pytest.fixture()
def keywords_fixture(mocker):
    def keywordstest_callback(request, context):
        data = dict(parse_qsl(request.body))
        query = data['QUERY']

        assert "WHERE isub0.res_subject ILIKE '%vizier%'" in query
        assert "WHERE 1=ivo_hasword(ires0.res_description, 'vizier')" in query
        assert "OR 1=ivo_hasword(ires0.res_title, 'vizier')" in query

        assert "WHERE isub1.res_subject ILIKE '%pulsar%'" in query
        assert "WHERE 1=ivo_hasword(ires1.res_description, 'pulsar')" in query
        assert "OR 1=ivo_hasword(ires1.res_title, 'pulsar')" in query

        assert "'ivo://ivoa.net/std/conesearch'" in query
        assert "'ivo://ivoa.net/std/sia'" in query
        assert "'ivo://ivoa.net/std/ssa'" in query
        assert "'ivo://ivoa.net/std/slap'" in query
        assert "'ivo://ivoa.net/std/tap'" in query

        return get_pkg_data_contents('data/regtap.xml')

    with mocker.register_uri(
        'POST', 'http://dc.g-vo.org/tap/sync',
        content=keywordstest_callback
    ) as matcher:
        yield matcher


@pytest.fixture()
def single_keyword_fixture(mocker):
    def keywordstest_callback(request, context):
        data = dict(parse_qsl(request.body))
        query = data['QUERY']

        assert "WHERE isub0.res_subject ILIKE '%single%'" in query
        assert "WHERE 1=ivo_hasword(ires0.res_description, 'single')" in query
        assert "OR 1=ivo_hasword(ires0.res_title, 'single')" in query

        assert "'ivo://ivoa.net/std/conesearch'" in query
        assert "'ivo://ivoa.net/std/sia'" in query
        assert "'ivo://ivoa.net/std/ssa'" in query
        assert "'ivo://ivoa.net/std/slap'" in query
        assert "'ivo://ivoa.net/std/tap'" in query

        return get_pkg_data_contents('data/regtap.xml')

    with mocker.register_uri(
        'POST', 'http://dc.g-vo.org/tap/sync',
        content=keywordstest_callback
    ) as matcher:
        yield matcher


@pytest.fixture()
def servicetype_fixture(mocker):
    def servicetypetest_callback(request, context):
        data = dict(parse_qsl(request.body))
        query = data['QUERY']

        assert "'ivo://ivoa.net/std/conesearch'" not in query
        assert "'ivo://ivoa.net/std/sia'" not in query
        assert "'ivo://ivoa.net/std/ssa'" not in query
        assert "'ivo://ivoa.net/std/slap'" not in query
        assert "'ivo://ivoa.net/std/tap'" in query

        return get_pkg_data_contents('data/regtap.xml')

    with mocker.register_uri(
        'POST', 'http://dc.g-vo.org/tap/sync',
        content=servicetypetest_callback
    ) as matcher:
        yield matcher


@pytest.fixture()
def waveband_fixture(mocker):
    def wavebandtest_callback(request, content):
        data = dict(parse_qsl(request.body))
        query = data['QUERY']

        assert "1 = ivo_hashlist_has(rr.resource.waveband, 'optical'" in query

        return get_pkg_data_contents('data/regtap.xml')

    with mocker.register_uri(
        'POST', 'http://dc.g-vo.org/tap/sync',
        content=wavebandtest_callback
    ) as matcher:
        yield matcher


@pytest.fixture()
def datamodel_fixture(mocker):
    def datamodeltest_callback(request, content):
        data = dict(parse_qsl(request.body))
        query = data['QUERY']

        assert (
            "WHERE idet.detail_xpath = '/capability/dataModel/@ivo-id" in query
        )
        assert "idet.detail_value, 'ivo://ivoa.net/std/tap%')" in query

        return get_pkg_data_contents('data/regtap.xml')

    with mocker.register_uri(
        'POST', 'http://dc.g-vo.org/tap/sync',
        content=datamodeltest_callback
    ) as matcher:
        yield matcher


@pytest.mark.usefixtures('keywords_fixture', 'capabilities')
def test_keywords():
    regsearch(keywords=['vizier', 'pulsar'])


@pytest.mark.usefixtures('single_keyword_fixture', 'capabilities')
def test_single_keyword():
    regsearch(keywords=['single'])
    regsearch(keywords='single')


@pytest.mark.usefixtures('servicetype_fixture', 'capabilities')
def test_servicetype():
    regsearch(servicetype='tap')


@pytest.mark.usefixtures('waveband_fixture', 'capabilities')
def test_waveband():
    regsearch(waveband='optical')


@pytest.mark.usefixtures('datamodel_fixture', 'capabilities')
def test_datamodel():
    regsearch(datamodel='tap')
