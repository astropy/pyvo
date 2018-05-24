#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.dal.sia
"""
from __future__ import (
    absolute_import, division, print_function, unicode_literals)


from functools import partial
import re

import pytest

from pyvo.dal.sia import search, SIAService

from astropy.utils.data import get_pkg_data_contents

get_pkg_data_contents = partial(
    get_pkg_data_contents, package=__package__, encoding='binary')

sia_re = re.compile('http://example.com/sia.*')


@pytest.fixture(autouse=True, scope='module')
def register_mocks(mocker):
    mocker.register_uri(
        'GET', 'http://example.com/querydata/image.fits',
        content=get_pkg_data_contents('data/querydata/image.fits')
    )


@pytest.fixture()
def sia(mocker):
    with mocker.register_uri(
        'GET', sia_re, content=get_pkg_data_contents('data/sia/dataset.xml')
    ) as matcher:
        yield matcher


def _test_result(result):
    assert result.getdataurl() == 'http://example.com/querydata/image.fits'
    assert result.filesize == 153280


@pytest.mark.usefixtures('sia')
def test_search():
    results = search('http://example.com/sia', pos=(288, 15))
    result = results[0]

    _test_result(result)


class TestSIAService(object):
    @pytest.mark.usefixtures('sia')
    def test_search(self):
        service = SIAService('http://example.com/sia')

        results = service.search(pos=(288, 15))
        result = results[0]

        _test_result(result)
