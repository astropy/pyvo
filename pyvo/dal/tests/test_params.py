#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.dal.datalink
"""
from functools import partial
from urllib.parse import parse_qsl

from pyvo.dal.adhoc import DatalinkResults
from pyvo.dal.params import find_param_by_keyword, get_converter
from pyvo.dal.exceptions import DALServiceError

import pytest

import numpy as np
import astropy.units as u
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


@pytest.fixture()
def proc_ds(mocker):
    def callback(request, context):
        return b''

    with mocker.register_uri(
        'GET', 'http://example.com/proc', content=callback
    ) as matcher:
        yield matcher


@pytest.fixture()
def proc_units(mocker):
    def callback(request, context):
        return get_pkg_data_contents('data/datalink/proc_units.xml')

    with mocker.register_uri(
        'GET', 'http://example.com/proc_units', content=callback
    ) as matcher:
        yield matcher


@pytest.fixture()
def proc_units_ds(mocker):
    def callback(request, context):
        data = dict(parse_qsl(request.query))
        if 'band' in data:
            assert data['band'] == (
                '6.000000000000001e-07 8.000000000000001e-06')

        return b''

    with mocker.register_uri(
        'GET', 'http://example.com/proc_units_ds', content=callback
    ) as matcher:
        yield matcher


@pytest.fixture()
def proc_inf(mocker):
    def callback(request, context):
        return get_pkg_data_contents('data/datalink/proc_inf.xml')

    with mocker.register_uri(
        'GET', 'http://example.com/proc_inf', content=callback
    ) as matcher:
        yield matcher


@pytest.fixture()
def proc_inf_ds(mocker):
    def callback(request, context):
        data = dict(parse_qsl(request.query))
        if 'band' in data:
            assert data['band'] == (
                '6.000000000000001e-07 +Inf')

        return b''

    with mocker.register_uri(
        'GET', 'http://example.com/proc_inf_ds', content=callback
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

    circle_lower = find_param_by_keyword('circle', input_params)
    circle_upper = find_param_by_keyword('CIRCLE', input_params)

    assert polygon_lower == polygon_upper
    assert circle_lower == circle_upper


@pytest.mark.usefixtures('proc')
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W06")
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W48")
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.E02")
def test_serialize():
    datalink = DatalinkResults.from_result_url('http://example.com/proc')
    proc = datalink[0]
    input_params = {param.name: param for param in proc.input_params}

    polygon_conv = get_converter(
        find_param_by_keyword('polygon', input_params))
    circle_conv = get_converter(
        find_param_by_keyword('circle', input_params))
    scale_conv = get_converter(
        find_param_by_keyword('scale', input_params))
    kind_conv = get_converter(
        find_param_by_keyword('kind', input_params))

    assert polygon_conv.serialize((1, 2, 3)) == "1 2 3"
    assert polygon_conv.serialize(np.array((1, 2, 3))) == "1 2 3"

    assert circle_conv.serialize((1.1, 2.2, 3.3)) == "1.1 2.2 3.3"
    assert circle_conv.serialize(np.array((1.1, 2.2, 3.3))) == "1.1 2.2 3.3"

    assert scale_conv.serialize(1) == "1"
    assert kind_conv.serialize("DATA") == "DATA"


@pytest.mark.usefixtures('proc')
@pytest.mark.usefixtures('proc_ds')
def test_serialize_exceptions():
    datalink = DatalinkResults.from_result_url('http://example.com/proc')
    proc = datalink[0]
    input_params = {param.name: param for param in proc.input_params}

    polygon_conv = get_converter(
        find_param_by_keyword('polygon', input_params))
    circle_conv = get_converter(
        find_param_by_keyword('circle', input_params))
    band_conv = get_converter(
        find_param_by_keyword('band', input_params))

    with pytest.raises(DALServiceError):
        polygon_conv.serialize((1, 2, 3, 4))

    with pytest.raises(DALServiceError):
        circle_conv.serialize((1, 2, 3, 4))

    with pytest.raises(DALServiceError):
        band_conv.serialize((1, 2, 3))


@pytest.mark.usefixtures('proc_units')
@pytest.mark.usefixtures('proc_units_ds')
def test_units():
    datalink = DatalinkResults.from_result_url('http://example.com/proc_units')
    proc = datalink[0]

    proc.process(band=(6000*u.Angstrom, 80000*u.Angstrom))


@pytest.mark.usefixtures('proc_inf')
@pytest.mark.usefixtures('proc_inf_ds')
def test_inf():
    datalink = DatalinkResults.from_result_url('http://example.com/proc_inf')
    proc = datalink[0]

    proc.process(band=(6000, +np.inf) * u.Angstrom)
