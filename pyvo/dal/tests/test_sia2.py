#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.dal.sia
"""
from functools import partial
import re

import pytest

from pyvo.dal.sia2 import search, SIAService

from astropy.io.fits import HDUList
from astropy.coordinates import SkyCoord
import astropy.units as u
from astropy.utils.data import get_pkg_data_contents

get_pkg_data_contents = partial(
    get_pkg_data_contents, package=__package__, encoding='binary')

sia_re = re.compile('https://example.com/sia/v2query.*')
capabilities_url = 'https://example.com/sia/capabilities'


@pytest.fixture(autouse=True, scope='module')
def register_mocks(mocker):
    with mocker.register_uri(
        'GET', 'https://example.com/querydata/image.fits',
        content=get_pkg_data_contents('data/querydata/image.fits')
    ) as matcher:
        yield matcher


@pytest.fixture()
def sia(mocker):
    with mocker.register_uri(
        'GET', sia_re, content=get_pkg_data_contents('data/sia2/dataset.xml')
    ) as matcher:
        yield matcher


@pytest.fixture()
def capabilities(mocker):
    with mocker.register_uri(
        'GET', capabilities_url,
            content=get_pkg_data_contents('data/sia2/capabilities.xml')
    ) as matcher:
        yield matcher


def _test_result(record):
    assert record.collection == 'TEST'
    assert record.id == 'TEST-DATASET'
    assert record.instrument == 'TEST-INSTR'
    assert record.facility == 'TEST-1.6m'


@pytest.mark.usefixtures('sia')
@pytest.mark.usefixtures('capabilities')
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W06")
def test_search():
    results = search('https://example.com/sia',
                     pos=(SkyCoord('08h45m07.5s +54d18m00s'), 0.0166*u.degree))
    result = results[0]

    _test_result(result)


class TestSIAService:
    @pytest.mark.usefixtures('sia')
    @pytest.mark.usefixtures('capabilities')
    @pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W06")
    @pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W42")
    @pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W49")
    def test_search(self):
        service = SIAService('https://example.com/sia')

        positions = [
            (SkyCoord('08h45m07.5s +54d18m00s'),
             0.0166 * u.degree),
            (12.0*u.degree, 12.5*u.degree, 34.0*u.degree, 36.0*u.degree),
            (SkyCoord(12.0*u.degree, 34.0*u.degree),
             SkyCoord(14.0*u.degree, 35.0*u.degree),
             SkyCoord(14.0*u.degree, 36.0*u.degree),
             SkyCoord(12.0*u.degree, 35.0*u.degree))]

        # each position
        for pos in positions:
            results = service.search(pos=pos)
            result = results[0]
            _test_result(result)
            
        # all positions
        results = service.search(pos=positions)
        result = results[0]
        _test_result(result)


