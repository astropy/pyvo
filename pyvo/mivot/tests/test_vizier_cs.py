'''
The first service in operation the annotates query responses in the fly is Vizier
https://cds/viz-bin/mivotconesearch/VizierParams
Data are mapped o the EPochPropagtion model as it is implemented in the current code.
This test case is based on 2 VOTables:
- The Vizier native (vizier_cs_withname.xml) where all ATTRIBUTE@ref are
  based on FIELD@name even when a field has an ID.
- The patched vizier (vizier_cs_withid.xml) where all ATTRIBUTE@ref are
  based on FIELD@ID or FIELD@name if it exists.
The test checks that:
- The position fields can be retrieved through the mapping.
- Both cases give the same results
A third test checks the case where
Created on 26 janv. 2024
@author: michel
'''
import os
import pytest
from urllib.request import urlretrieve
from pyvo.mivot.version_checker import check_astropy_version
from pyvo.mivot.viewer.mivot_viewer import MivotViewer
from pyvo.mivot.utils.exceptions import ResolveException


@pytest.fixture
def data_path():
    return os.path.dirname(os.path.realpath(__file__))


@pytest.fixture
def data_sample_url():
    return "https://raw.githubusercontent.com/ivoa/dm-usecases/main/pyvo-ci-sample/"


@pytest.fixture
def delt_coo():
    """ acceptable delta for coordinate value comparisons
    """
    return 0.0000005


@pytest.fixture
def path_to_withname(data_path, data_sample_url):
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")

    votable_name = "vizier_cs_withname.xml"
    votable_path = os.path.join(data_path, "data", votable_name)
    urlretrieve(data_sample_url + votable_name,
                votable_path)

    yield votable_path
    os.remove(votable_path)


@pytest.fixture
def path_to_withid(data_path, data_sample_url):
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")

    votable_name = "vizier_cs_withid.xml"
    votable_path = os.path.join(data_path, "data", votable_name)
    urlretrieve(data_sample_url + votable_name,
                votable_path)

    yield votable_path
    os.remove(votable_path)


@pytest.fixture
def path_to_badref(data_path, data_sample_url):
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")

    votable_name = "vizier_cs_badref.xml"
    votable_path = os.path.join(data_path, "data", votable_name)
    urlretrieve(data_sample_url + votable_name,
                votable_path)

    yield votable_path
    os.remove(votable_path)


@pytest.mark.remote_data
def test_with_name(path_to_withname, delt_coo):
    """ Test that the epoch propagation works with all FIELDs referenced by name or by ID
    """
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")

    m_viewer = MivotViewer(votable_path=path_to_withname)
    m_viewer.get_next_row()
    mivot_object = m_viewer.instance

    assert abs(mivot_object.longitude.value - 52.2340018) < delt_coo
    assert abs(mivot_object.latitude.value - 59.8937333) < delt_coo
    assert abs(mivot_object.pmLongitude.value - 1.5) < delt_coo
    assert abs(mivot_object.pmLatitude.value - -12.30000019) < delt_coo
    assert str(mivot_object.epoch.value) == '2013.418'
    assert str(mivot_object.Coordinate_coordSys.spaceRefFrame.value) == 'ICRS'

    m_viewer.next_row()

    assert abs(mivot_object.longitude.value - 32.2340018) < delt_coo
    assert abs(mivot_object.latitude.value - 49.8937333) < delt_coo
    assert abs(mivot_object.pmLongitude.value - 1.5) < delt_coo
    assert abs(mivot_object.pmLatitude.value - -12.30000019) < delt_coo
    assert str(mivot_object.epoch.value) == '2013.418'
    assert str(mivot_object.Coordinate_coordSys.spaceRefFrame.value) == 'ICRS'

@pytest.mark.remote_data
def test_with_id(path_to_withid, delt_coo):
    """ Test that the epoch propagation works with all FIELDs referenced by name or by ID
    """
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")
    # Test with all FILELDs referenced by names
    m_viewer = MivotViewer(votable_path=path_to_withid)
    m_viewer.get_next_row()
    mivot_instance = m_viewer.instance
    assert abs(mivot_instance.longitude.value - 52.2340018) < delt_coo
    assert abs(mivot_instance.latitude.value - 59.8937333) < delt_coo
    assert abs(mivot_instance.pmLongitude.value - 1.5) < delt_coo
    assert abs(mivot_instance.pmLatitude.value - -12.30000019) < delt_coo
    assert str(mivot_instance.epoch.value) == '2013.418'


@pytest.mark.remote_data
def test_bad_ref(path_to_badref, delt_coo):
    """ Test that the epoch propagation works with all FIELDs referenced by name or by ID
    """
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")
    # Test with all FILELDs referenced by names
    with (pytest.raises(ResolveException, match="Attribute mango:EpochPosition.epoch can not be set.*")):
        MivotViewer(votable_path=path_to_badref)


if __name__ == '__main__':
    pytest.main()
