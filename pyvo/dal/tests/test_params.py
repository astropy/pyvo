#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.dal.datalink
"""
from __future__ import (
    absolute_import, division, print_function, unicode_literals)

from functools import partial

from pyvo.dal.adhoc import DatalinkResults
from pyvo.dal.params import find_param_by_keyword

import pytest

from astropy.utils.data import get_pkg_data_contents, get_pkg_data_fileobj

get_pkg_data_contents = partial(
    get_pkg_data_contents, package=__package__, encoding='binary')

get_pkg_data_fileobj = partial(
    get_pkg_data_fileobj, package=__package__, encoding='binary')


@pytest.fixture()
def proc(mocker):
    def callback(request, context):
        return get_pkg_data_contents('data/datalink/proc.xml')

    with mocker.register_uri(
        'GET', 'http://example.com/proc', content=callback
    ) as matcher:
        yield matcher


@pytest.mark.usefixtures('proc')
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W06")
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W48")
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.E02")
def test_find_param_by_keyword():
    datalink = DatalinkResults.from_result_url('http://example.com/proc')
    proc = datalink[0]
    input_params = {param.name: param for param in proc.input_params}

    polygon_lower = find_param_by_keyword('polygon', input_params)
    polygon_upper = find_param_by_keyword('POLYGON', input_params)

    assert polygon_lower == polygon_upper
