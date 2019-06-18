#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.dal.datalink
"""
from functools import partial

import pytest

import pyvo as vo

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
        'GET', 'http://example.com/datalink', content=callback
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
