#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.registry.regtap
"""
from functools import partial
from urllib.parse import parse_qsl
import pytest

from pyvo.registry import regtap
from pyvo.registry import search as regsearch
from pyvo.dal import query as dalq
from pyvo.dal import tap

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

        assert "res_subject ILIKE '%vizier%'" in query
        assert "ivo_hasword(res_description, 'vizier')" in query
        assert "1=ivo_hasword(res_title, 'vizier')" in query

        assert " res_subject ILIKE '%pulsar%'" in query
        assert "1=ivo_hasword(res_description, 'pulsar')" in query
        assert "1=ivo_hasword(res_title, 'pulsar')" in query

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

        assert "WHERE res_subject ILIKE '%single%'" in query
        assert "WHERE 1=ivo_hasword(res_description, 'single') UNION" in query
        assert "1=ivo_hasword(res_title, 'single')" in query

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
            "(detail_xpath = '/capability/dataModel/@ivo-id'" in query)

        assert (
            "ivo_nocasematch(detail_value, 'ivo://ivoa.net/std/obscore%'))"
            in query)

        return get_pkg_data_contents('data/regtap.xml')

    with mocker.register_uri(
        'POST', 'http://dc.g-vo.org/tap/sync',
        content=datamodeltest_callback
    ) as matcher:
        yield matcher


@pytest.fixture()
def aux_fixture(mocker):
    def auxtest_callback(request, context):
        data = dict(parse_qsl(request.body))
        query = data['QUERY']

        assert "ivo://ivoa.net/std/tap#aux" in query

        return get_pkg_data_contents('data/regtap.xml')

    with mocker.register_uri(
        'POST', 'http://dc.g-vo.org/tap/sync',
        content=auxtest_callback
    ) as matcher:
        yield matcher


class TestInterfaceClass:
    def test_basic(self):
        intf = regtap.Interface("http://example.org", "", "", "")
        assert intf.access_url == "http://example.org"
        assert intf.standard_id is None
        assert intf.type is None
        assert intf.role is None
        assert intf.is_standard == False

    def test_unknown_standard(self):
        intf = regtap.Interface("http://example.org", "ivo://gavo/std/a", 
            "vs:paramhttp", "std")
        assert intf.is_standard
        with pytest.raises(ValueError) as excinfo:
            intf.to_service()

        assert str(excinfo.value) == (
            "PyVO has no support for interfaces with standard"
            " id ivo://gavo/std/a.")

    def test_known_standard(self):
        intf = regtap.Interface("http://example.org", 
            "ivo://ivoa.net/std/tap#aux", "vs:paramhttp", "std")
        assert isinstance(intf.to_service(), tap.TAPService)

    def test_secondary_interface(self):
        intf = regtap.Interface("http://example.org", 
            "ivo://ivoa.net/std/tap#aux",
            "vs:webbrowser", "web")

        with pytest.raises(ValueError) as excinfo:
            intf.to_service()

        assert str(excinfo.value) == (
            "This is not a standard interface.  PyVO cannot speak to it.")


@pytest.mark.usefixtures('keywords_fixture', 'capabilities')
def test_keywords():
    regsearch(keywords=['vizier', 'pulsar'])


@pytest.mark.usefixtures('single_keyword_fixture', 'capabilities')
def test_single_keyword():
    regsearch(keywords=['single'])
    regsearch(keywords='single')


@pytest.mark.usefixtures('servicetype_fixture', 'capabilities')
def test_servicetype():
    regsearch(servicetype='table')


@pytest.mark.usefixtures('waveband_fixture', 'capabilities')
def test_waveband():
    regsearch(waveband='optical')


@pytest.mark.usefixtures('datamodel_fixture', 'capabilities')
def test_datamodel():
    regsearch(datamodel='ObsCore')


@pytest.mark.usefixtures('aux_fixture', 'capabilities')
def test_servicetype_aux():
    regsearch(servicetype='table', includeaux=True)


@pytest.mark.usefixtures('aux_fixture', 'capabilities')
def test_bad_servicetype_aux():
    with pytest.raises(dalq.DALQueryError):
        regsearch(servicetype='bad_servicetype', includeaux=True)


class TestInterfaceSelection:
    def test_interfaces_shown(self):
        print(regtap.get_RegTAP_query(ivoid="ivo://org.gavo.dc/flashheros/q/ssa"))
