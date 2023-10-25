# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.discover.image
"""

import pytest

from astropy import time
from astropy import units as u

from pyvo import dal
from pyvo import discover
from pyvo import registry
from pyvo.discover import image
from pyvo.utils.testing import LearnableRequestMocker


@pytest.fixture
def _all_constraint_responses(requests_mock):
    matcher = LearnableRequestMocker("image-with-all-constraints")
    requests_mock.add_matcher(matcher)


@pytest.fixture
def _sia1_responses(requests_mock):
    matcher = LearnableRequestMocker("sia1-responses")
    requests_mock.add_matcher(matcher)


def test_no_services_selected():
    with pytest.raises(dal.DALQueryError) as excinfo:
        image.ImageDiscoverer().query_services()
    assert "No services to query." in str(excinfo.value)


def test_single_sia1(_sia1_responses):
    sia_svc = registry.search(registry.Ivoid("ivo://org.gavo.dc/bgds/q/sia"))
    discoverer = image.ImageDiscoverer(
        space=(116, -29, 0.1),
        time=time.Time(56383.105520834, format="mjd"))
    discoverer.set_services(sia_svc)
    discoverer.query_services()
    im = discoverer.results[0]
    assert im.s_xel1 == 10800.
    assert isinstance(im.em_min, float)
    assert abs(im.s_dec+29)<2
    assert im.instrument_name == 'Robotic Bochum Twin Telescope (RoBoTT)'
    assert "BGDS GDS_" in im.obs_title
    assert "dc.zah.uni-heidelberg.de/getproduct/bgds/data" in im.access_url


def test_cone_and_spectral_point(_all_constraint_responses):
    images, logs = discover.images_globally(
        space=(134, 11, 0.1),
        spectrum=600*u.eV)

    assert ("SIA2 service <ivo://org.gavo.dc/__system__/siap2/sitewide>: 8 recs"
        in logs)

    assert len(images) == 8
    assert images[0].obs_collection == "RASS"

    # expected failure: the rosat SIA1 record should be filtered out
    # by its relationship to the sitewide SIA2
    assert len(logs) == 1


@pytest.fixture
def _servedby_elision_responses(requests_mock):
    matcher = LearnableRequestMocker("servedby-elision-responses")
    requests_mock.add_matcher(matcher)


def test_servedby_elision(_servedby_elision_responses):
    d = discover.ImageDiscoverer(space=(3, 1, 0.2))
    # siap2/sitewide has isservedby to tap
    d.set_services(registry.search(registry.Ivoid(
       "ivo://org.gavo.dc/tap",
       "ivo://org.gavo.dc/__system__/siap2/sitewide")))

    assert d.sia2_recs == []
    assert len(d.obscore_recs) == 1
    assert d.obscore_recs[0].ivoid == "ivo://org.gavo.dc/tap"
    assert ('Skipping ivo://org.gavo.dc/__system__/siap2/sitewide because it is served by ivo://org.gavo.dc/tap'
        in d.log_messages)
