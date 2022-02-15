#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.dal.datalink
"""
from functools import partial

import pytest

import pyvo as vo
from pyvo.dal.adhoc import DatalinkResults

from astropy.utils.data import get_pkg_data_contents

get_pkg_data_contents = partial(
    get_pkg_data_contents, package=__package__, encoding='binary')


@pytest.fixture()
def ssa_datalink(mocker):
    def callback(request, context):
        return get_pkg_data_contents('data/datalink/datalink-ssa.xml')

    with mocker.register_uri(
        'GET', 'http://example.com/ssa_datalink', content=callback
    ) as matcher:
        yield matcher


@pytest.fixture()
def datalink(mocker):
    def callback(request, context):
        return get_pkg_data_contents('data/datalink/datalink.xml')

    with mocker.register_uri(
        'POST', 'http://example.com/datalink', content=callback
    ) as matcher:
        yield matcher


@pytest.fixture()
def obscore_datalink(mocker):
    def callback(request, context):
        return get_pkg_data_contents('data/datalink/datalink-obscore.xml')

    with mocker.register_uri(
        'GET', 'http://example.com/obscore', content=callback
    ) as matcher:
        yield matcher


@pytest.fixture()
def res_datalink(mocker):

    first_batch = True

    def callback(request, context):
        nonlocal first_batch
        if first_batch:
            first_batch = False
            return get_pkg_data_contents('data/datalink/cutout1.xml')
        else:
            return get_pkg_data_contents('data/datalink/cutout2.xml')

    with mocker.register_uri(
        'POST', 'https://example.com/obscore-datalink', content=callback
    ) as matcher:
        yield matcher


@pytest.fixture()
def proc(mocker):
    def callback(request, context):
        return get_pkg_data_contents('data/datalink/proc.xml')

    with mocker.register_uri(
        'GET', 'http://example.com/proc', content=callback
    ) as matcher:
        yield matcher


@pytest.mark.usefixtures('ssa_datalink', 'datalink')
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W27")
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W06")
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W48")
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.E02")
def test_datalink():
    results = vo.spectrumsearch(
        'http://example.com/ssa_datalink', (30, 30))

    datalink = next(results.iter_datalinks())

    row = datalink[0]
    assert row.semantics == "#progenitor"

    row = datalink[1]
    assert row.semantics == "#proc"

    row = datalink[2]
    assert row.semantics == "#this"

    row = datalink[3]
    assert row.semantics == "#preview"


@pytest.mark.usefixtures('obscore_datalink', 'res_datalink')
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W27")
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W06")
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W48")
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.E02")
def test_datalink_batch():
    results = vo.dal.imagesearch(
        'http://example.com/obscore', (30, 30))

    assert len([_ for _ in results.iter_datalinks()]) == 3


# temporary hack while astropy <4.1 is still around; you can remove
# this and its calls once that's no longer true.
def _debytify(v):
    if isinstance(v, bytes):
        return v.decode("utf-8")
    return v


@pytest.mark.usefixtures('proc')
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W27")
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W06")
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W48")
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.E02")
class TestSemanticsRetrieval:
    def test_access_with_string(self):
        datalink = DatalinkResults.from_result_url('http://example.com/proc')
        res = [_debytify(r["access_url"])
            for r in datalink.bysemantics("#this")]
        assert len(res)==1
        assert res[0].endswith("eq010000ms/20100927.comb_avg.0001.fits.fz")

    def test_access_with_list(self):
        datalink = DatalinkResults.from_result_url('http://example.com/proc')
        res = [_debytify(r["access_url"])
            for r in datalink.bysemantics(["#this", "#preview-image"])]
        assert len(res)==2
        assert res[0].endswith("eq010000ms/20100927.comb_avg.0001.fits.fz")
        assert res[1].endswith("20100927.comb_avg.0001.fits.fz?preview=True")

    def test_access_with_expansion(self):
        datalink = DatalinkResults.from_result_url('http://example.com/proc')
        res = [_debytify(r["access_url"])
            for r in datalink.bysemantics(["#this", "#preview"])]
        assert len(res)==3
        assert res[0].endswith("eq010000ms/20100927.comb_avg.0001.fits.fz")
        assert res[1].endswith("20100927.comb_avg.0001.fits.fz?preview=True")
        assert res[2].endswith("http://dc.zah.uni-heidelberg.de/wider.dat")

    def test_access_without_expansion(self):
        datalink = DatalinkResults.from_result_url('http://example.com/proc')
        res = [_debytify(r["access_url"])
            for r in datalink.bysemantics(
               ["#this", "#preview"],
               include_narrower=False)]
        assert len(res)==2
        assert res[0].endswith("eq010000ms/20100927.comb_avg.0001.fits.fz")
        assert res[1].endswith("http://dc.zah.uni-heidelberg.de/wider.dat")

    def test_with_full_url(self):
        datalink = DatalinkResults.from_result_url('http://example.com/proc')
        res = [_debytify(r["access_url"])
            for r in datalink.bysemantics("urn:example:rdf/dlext#oracle")]
        assert len(res)==1
        assert res[0].endswith("when-will-it-be-back")

    def test_all_mixed(self):
        datalink = DatalinkResults.from_result_url('http://example.com/proc')
        res = [_debytify(r["access_url"])
            for r in datalink.bysemantics([
                "urn:example:rdf/dlext#oracle",
                'http://www.ivoa.net/rdf/datalink/core#preview',
                '#this',
                'non-existing-term'])]
        assert len(res)==4
        assert res[0].endswith("eq010000ms/20100927.comb_avg.0001.fits.fz")
        assert res[1].endswith("comb_avg.0001.fits.fz?preview=True")
        assert res[2].endswith("http://dc.zah.uni-heidelberg.de/wider.dat")
        assert res[3].endswith("when-will-it-be-back")
