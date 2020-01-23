#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.dal.sia
"""
from functools import partial
import re

import pytest

from pyvo.dal.sia import search, SIAService, search_v2

from astropy.io.fits import HDUList
from astropy.coordinates import SkyCoord
import astropy.units as u
from astropy.utils.data import get_pkg_data_contents

get_pkg_data_contents = partial(
    get_pkg_data_contents, package=__package__, encoding='binary')

sia_re = re.compile('http://example.com/sia.*')


@pytest.fixture(autouse=True, scope='module')
def register_mocks(mocker):
    with mocker.register_uri(
        'GET', 'http://example.com/querydata/image.fits',
        content=get_pkg_data_contents('data/querydata/image.fits')
    ) as matcher:
        yield matcher


@pytest.fixture()
def sia(mocker):
    with mocker.register_uri(
        'GET', sia_re, content=get_pkg_data_contents('data/sia/dataset.xml')
    ) as matcher:
        yield matcher


def _test_result(result):
    assert result.getdataurl() == 'http://example.com/querydata/image.fits'
    assert isinstance(result.getdataobj(), HDUList)
    assert result.filesize == 153280


@pytest.mark.usefixtures('sia')
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W06")
def test_search():
    results = search('http://example.com/sia', pos=(288, 15))
    result = results[0]

    _test_result(result)


class TestSIAService:
    @pytest.mark.usefixtures('sia')
    @pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W06")
    @pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W42")
    @pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W49")
    def test_search(self):
        service = SIAService('http://example.com/sia')

        results = service.search(pos=(288, 15))
        result = results[0]

        _test_result(result)

    @pytest.mark.usefixtures('sia')
    @pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W06")
    @pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W42")
    @pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W49")
    def test_search(self):
        service = SIAService('http://example.com/sia')

        positions = [
            'CIRCLE 12.0 34.0 0.5',
            'RANGE 12.0 12.5 34.0 36.0',
            'POLYGON 12.0 34.0 14.0 35.0 14.0 36.0 12.0 35.0',
            (SkyCoord('08h45m07.5s +54d18m00s'),
             0.0166 * u.degree),
            (12.0*u.degree, 12.5*u.degree, 34.0*u.degree, 36.0*u.degree),
            (SkyCoord(12.0*u.degree, 34.0*u.degree),
             SkyCoord(14.0*u.degree, 35.0*u.degree),
             SkyCoord(14.0*u.degree, 36.0*u.degree),
             SkyCoord(12.0*u.degree, 35.0*u.degree))]

        for pos in positions:
            results = service.search_v2(pos=pos)
            result = results[0]
            _test_result(result)


@pytest.mark.usefixtures('sia')
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W06")
def test_search_v2():
    results = search_v2('http://example.com/sia', pos='CIRCLE 12.0 34.0 0.5')
    result = results[0]

    _test_result(result)

