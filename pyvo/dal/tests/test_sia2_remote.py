#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.dal.sia2 against remote services
"""

import pytest

from pyvo.dal.sia2 import search, SIAService

import astropy.units as u

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
        # check attributes of a record
        record = results[0]
        record.data_type
        record.data_subtype
        record.calib_level

        #          TARGET INFO
        record.target_name
        record.target_class

        #           DATA DESCRIPTION
        record.id
        record.title
        record.collection
        record.create_date
        record.creator_name
        record.creator_did

        #          CURATION INFORMATION
        record.release_date
        record.publisher_id
        record.publisher_did
        record.bib_reference
        record.data_rights

        #            ACCESS INFORMATION
        record.access_url
        record.res_format
        record.access_estsize

        #            SPATIAL CHARACTERISATION
        record.pos
        record.radius
        record.region
        record.spatial_resolution
        record.spatial_xel
        record.spatial_ucd
        record.spatial_unit
        record.resolution_min
        record.resolution_max
        record.spatial_calib_status
        record.spatial_stat_error
        record.pixel_scale

        #            TIME CHARACTERISATION
        record.time_xel
        record.ref_pos
        record.time_bounds
        record.exptime
        record.time_resolution
        record.time_calib_status
        record.time_stat_error

        #            SPECTRAL CHARACTERISATION
        record.spectral_xel
        record.spectral_ucd
        record.spectral_unit
        record.spectral_calib_status
        record.spectral_bounds
        record.resolving_power
        record.resolving_power_min
        record.resolving_power_max
        record.spectral_resolution
        record.spectral_stat_error

        #            OBSERVABLE AXIS
        record.obs_ucd
        record.obs_unit
        record.obs_calib_status
        record.obs_stat_error

        #            POLARIZATION CHARACTERISATION
        record.pol_xel
        record.pol

        #            PROVENANCE
        record.instrument
        record.facility
        record.proposal_id

    def test_band(self):
        results = search(CADC_SIA_URL, band=(0.0002, 0.0003), maxrec=5)
        # TODO - correctness
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
        assert results[0].publisher_did in global_ids
        assert results[1].publisher_did in global_ids

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
