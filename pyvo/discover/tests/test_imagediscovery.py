# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.discover.image
"""

import pytest

from astropy import time
from astropy import units as u

from pyvo import discover
from pyvo.utils.testing import LearnableRequestMocker


@pytest.fixture
def _all_constraint_responses(requests_mock):
    matcher = LearnableRequestMocker("image-with-all-constraints")
    requests_mock.add_matcher(matcher)


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
