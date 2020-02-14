#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.dal.sia2 against remote services
"""
from functools import partial
import re

import pytest

from pyvo.dal.sia2 import search, SIAService

import astropy.units as u
from astropy.utils.data import get_pkg_data_contents

CADC_SIA_URL = 'https://www.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/sia'

@pytest.mark.remote_data
class TestSIACadc():
    # Tests the SIA2 client against the CADC SIA service

    def test_service(self):
        cadc = SIAService(baseurl=CADC_SIA_URL)
        assert cadc.availability
        assert cadc.availability.available
        assert cadc.availability.notes
        assert cadc.availability.notes[0] == 'service is accepting queries'
        assert cadc.capabilities

    def test_pos(self):
        results = search(CADC_SIA_URL, pos=(2.8425, 74.4846, 0.001))
        assert len(results) > 10

        # limit results to 5 to expedite tests
        results = search(CADC_SIA_URL, pos=(2.8425, 74.4846, 0.001), maxrec=5)
        assert len(results) == 5

    def test_band(self):
        results = search(CADC_SIA_URL, band=(0.0002, 0.0003), maxrec=5)
        #TODO - correctness
        assert len(results) == 5

    def test_time(self):
        results = search(CADC_SIA_URL,
                         time=('2002-01-01T00:00:00.00',
                               '2002-01-02T00:00:00.00'),
                         maxrec=5)
        assert len(results) == 5

    def test_pol(self):
        results = search(CADC_SIA_URL, pol=['YY', 'U'], maxrec=5)
        assert len(results) == 5
        for rr in results:
            assert 'YY' in rr.pol or 'U' in rr.pol

    def test_fov(self):
        results = search(CADC_SIA_URL, field_of_view=(10, 20), maxrec=5)
        assert len(results) == 5
        # how to test values

    def test_spatial_res(self):
        results = search(CADC_SIA_URL, spatial_resolution=(1, 2), maxrec=5)
        assert len(results) == 5
        for rr in results:
            assert 1*u.arcsec <= rr.spatial_resolution <= 2*u.arcsec

    def test_spec_resp(self):
        results = search(CADC_SIA_URL, spectral_resolving_power=(1, 2), maxrec=5)
        assert len(results) == 5
        for rr in results:
            assert 1 <= rr.resolving_power <= 2

    def test_exptime(self):
        results = search(CADC_SIA_URL, exptime=(1, 2),
                        maxrec=5)
        assert len(results) == 5
        for rr in results:
            assert 1*u.second <= rr.exptime <= 2*u.second

    def test_timeres(self):
        results = search(CADC_SIA_URL, timeres=(1, 2),
                         maxrec=5)
        assert len(results) == 5
        for rr in results:
            assert 1 * u.second <= rr.time_resolution <= 2 * u.second

    def test_global_id(self):
        global_ids = ['ivo://cadc.nrc.ca/CFHT?447231/447231o',
                      'ivo://cadc.nrc.ca/CFHT?447232/447232o']
        results = search(CADC_SIA_URL, global_id=global_ids)
        assert len(results) == 2
        assert results[0].global_id in global_ids
        assert results[1].global_id in global_ids

    def test_facility(self):
        results = search(CADC_SIA_URL, facility='JCMT', maxrec=5)
        assert len(results) == 5
        for rr in results:
            assert rr.facility == 'JCMT'

    def test_collection(self):
        results = search(CADC_SIA_URL, collection='CFHT', maxrec=5)
        assert len(results) == 5
        for rr in results:
            assert rr.collection == 'CFHT'

    def test_instrument(self):
        results = search(CADC_SIA_URL, instrument='SCUBA-2', maxrec=5)
        assert len(results) == 5
        for rr in results:
            assert rr.instrument == 'SCUBA-2'

    def test_data_type(self):
        results = search(CADC_SIA_URL, data_type='image', maxrec=5)
        assert len(results) == 5
        for rr in results:
            assert rr.data_type == 'image'

    def test_target_name(self):
        results = search(CADC_SIA_URL, target_name='OGF:t028', maxrec=5)
        assert len(results) == 5
        for rr in results:
            assert rr.target_name == 'OGF:t028'

    def test_res_format(self):
        results = search(
            CADC_SIA_URL,
            res_format='application/x-votable+xml;content=datalink',
            maxrec=5)
        assert len(results) == 5
        for rr in results:
            assert rr.res_format == \
                   'application/x-votable+xml;content=datalink'





