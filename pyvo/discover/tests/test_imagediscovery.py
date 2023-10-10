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


def test_with_all_constraints(_all_constraint_responses):
    res = discover.images_globally(
        space=(132, 14, 0.1),
        time=time.Time(58794.9, format="mjd"),
        spectrum=600*u.eV)
