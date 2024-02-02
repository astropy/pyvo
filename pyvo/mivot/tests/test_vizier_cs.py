'''
The first service in operato the annotates query responses in the fly is Vizier
https://cds/viz-bin/mivotconesearch/VizierParams

Data are mapped o the EPochPropagtion model as it is implemented in the current code.
This test case is based on 2 VOTables:
- The Vizier native (vizier_cs_withname.xml) where all ATTRIBUTE@ref are based on FIELD@name even when a field has an ID.
- The patched vizier (vizier_cs_withid.xml) where all ATTRIBUTE@ref are based on FIELD@name or FIELD@name if it exists.

The test checks that:
- The position fields can be retrieved through the mapping.  
- Both cases give the same results

A third test checks the case where 
Created on 26 janv. 2024

@author: michel
'''
import os
import pytest
import astropy.units as u
from pyvo.mivot.version_checker import check_astropy_version
from astropy.coordinates import SkyCoord
from astropy.time import Time
from pyvo.mivot.viewer.model_viewer_level1 import ModelViewerLevel1
from pyvo.mivot.utils.exceptions import ResolveException

try:
    from erfa import ErfaWarning
except Exception:
    from astropy.utils.exceptions import ErfaWarning
@pytest.fixture
def data_path():
    return os.path.dirname(os.path.realpath(__file__))

@pytest.fixture
def delt_coo():
    """ acceptable delta for coordinate value comparisons
    """
    return 0.0000001


def test_with_name(data_path, delt_coo):  
    """ Test that the epoch propagation works with all FIELDs referenced by name or by ID
    """
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")
    
    # Test with all FILELDs referenced by names
    votable = os.path.join(data_path, "data/vizier_cs_withname.xml")
    m_viewer = ModelViewerLevel1(votable_path=votable)
    row_view = m_viewer.get_next_row_view()
    name_skycoo = row_view.epoch_propagation.sky_coordinate()    
    assert abs(name_skycoo.ra.value - 52.2340018) < delt_coo
    assert abs(name_skycoo.dec.value - 59.8937333) < delt_coo
    assert abs(name_skycoo.pm_ra_cosdec.value - 1.5) < delt_coo
    assert abs(name_skycoo.pm_dec.value - -12.30000019) < delt_coo
    assert str(name_skycoo.obstime) == '2013.418'
    # ERFA empits a warning when apply_space_motion is applied to a SKyCoo without distance.
    # The workaround bemow is take out of 
    # https://github.com/astropy/astropy/blob/main/astropy/coordinates/tests/test_sky_coord.py
    with pytest.warns(ErfaWarning, match='ERFA function "pmsafe" yielded .*'):
        moved_skycoo = name_skycoo.apply_space_motion(dt=+10* u.yr)

    assert abs(moved_skycoo.ra.value - 52.23401011) < delt_coo
    assert abs(moved_skycoo.dec.value - 59.89369913) < delt_coo
        
    # Test with all FILELDs but one (Epoch) referenced by names
    votable = os.path.join(data_path, "data/vizier_cs_withid.xml")
    m_viewer = ModelViewerLevel1(votable_path=votable)
    row_view = m_viewer.get_next_row_view()
    id_skycoo = row_view.epoch_propagation.sky_coordinate()    
    assert abs(id_skycoo.ra.value - 52.2340018) < delt_coo
    assert abs(id_skycoo.dec.value - 59.8937333) < delt_coo
    assert abs(id_skycoo.pm_ra_cosdec.value - 1.5) < delt_coo
    assert abs(id_skycoo.pm_dec.value - -12.30000019) < delt_coo
    assert str(id_skycoo.obstime) == '2013.418'
    
    with pytest.warns(ErfaWarning, match='ERFA function "pmsafe" yielded .*'):
        moved_skycoo = id_skycoo.apply_space_motion(dt=+10* u.yr)

    assert abs(moved_skycoo.ra.value - 52.23401011) < delt_coo
    assert abs(moved_skycoo.dec.value - 59.89369913) < delt_coo

    # make sure the epoch is the same in both cases
    assert str(name_skycoo.obstime) == str(id_skycoo.obstime)

def test_bad_ref(data_path, delt_coo):  
    """ Test that the epoch propagation works with all FIELDs referenced by name or by ID
    """
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")
    
    # Test with all FILELDs referenced by names
    votable = os.path.join(data_path, "data/vizier_cs_badref.xml")
    
    with (pytest.raises(ResolveException, match="Attribute mango:EpochPosition.epoch can not be set.*")):
        ModelViewerLevel1(votable_path=votable)
    
if __name__ == '__main__':
    pytest.main()

