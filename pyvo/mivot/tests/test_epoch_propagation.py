# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Test for mivot.seekers.annotation_seeker.py
"""
import os

import pytest
from astropy.coordinates import SkyCoord
import astropy.units as u
from astropy.time import Time

from pyvo.mivot.version_checker import check_astropy_version
from pyvo.mivot.viewer.model_viewer import ModelViewer
from pyvo.utils import activate_features

activate_features('MIVOT')


def test_epoch_propagation(m_viewer):
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")

    row_view = m_viewer.get_next_row_view()
    epoch_propagation = row_view.epoch_propagation
    assert epoch_propagation._sky_coord == row_view.sky_coordinate
    sky_coord_to_compare = (SkyCoord(distance=(row_view.parallax.value / 4) * u.pc,
                                     radial_velocity=row_view.radialVelocity.value * u.km / u.s,
                                     ra=row_view.longitude.value * u.degree,
                                     dec=row_view.latitude.value * u.degree,
                                     pm_ra_cosdec=row_view.latitude.value * u.mas / u.yr,
                                     pm_dec=row_view.pmLatitude.value * u.mas / u.yr,
                                     frame=row_view.Coordinate_coosys
                                     .PhysicalCoordSys_frame.spaceRefFrame.value.lower(),
                                     obstime=Time(row_view.epoch.value, format="decimalyear")))

    assert sky_coord_to_compare == epoch_propagation.SkyCoordinate()
    assert ((sky_coord_to_compare.apply_space_motion(dt=-42 * u.year).ra,
             sky_coord_to_compare.apply_space_motion(dt=-42 * u.year).dec)
            == epoch_propagation.apply_space_motion(dt=-42 * u.year))
    assert epoch_propagation.ref_long == 10.0
    assert epoch_propagation.ref_lat == 10.0
    assert epoch_propagation.ref_pm_long == 10.0
    assert epoch_propagation.ref_pm_lat == -20.0


@pytest.fixture
def m_viewer(data_path):
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")
    votable = os.path.join(data_path, "data/simple-annotation-votable.xml")
    return ModelViewer(votable_path=votable)


@pytest.fixture
def data_path():
    return os.path.dirname(os.path.realpath(__file__))


if __name__ == '__main__':
    pytest.main()
