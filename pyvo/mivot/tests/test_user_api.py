'''
Check the API exposed to the user works prperly
This unit test can also be used as a code example
Created on 26 Feb. 2024
@author: michel
'''
import os
import pytest
from urllib.request import urlretrieve
from pyvo.mivot.version_checker import check_astropy_version
from pyvo.mivot.viewer.mivot_viewer import MivotViewer
from astropy.io.votable import parse


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
    return 0.0000001


@pytest.fixture
def path_to_votable(data_path, data_sample_url):
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")

    votable_name = "vizier_for_user_api.vot"
    votable_path = os.path.join(data_path, "data", votable_name)
    urlretrieve(data_sample_url + votable_name,
                votable_path)

    yield votable_path
    os.remove(votable_path)




@pytest.mark.remote_data
def test_by_attribute(path_to_votable):
    """ check that the mivot object attribute are correct """
    mivot_viewer = MivotViewer(path_to_votable)
    cpt = 0
    while mivot_viewer.next_row():
        cpt += 1
    assert cpt == 6
    mivot_viewer.rewind()
    
    ref = [-0.36042119, 0.22293899, -0.07592034, -0.21749947, -0.1281483, -0.28005255]
    read = []
    while mivot_viewer.next_row():
        mivot_object = mivot_viewer.instance
        read.append(mivot_object.latitude.value)

    assert read == ref

@pytest.mark.remote_data
def test_external_iterator(path_to_votable, delt_coo):
    """ Checks the the values returned by MIVOT are 
    the same as those read by Astropy
    """
    # parse the VOTable outside of the viewer    
    votable = parse(path_to_votable)
    table = votable.resources[0].tables[0]
    # init the viewer
    mivot_viewer = MivotViewer(votable, resource_number=0)
    mivot_object = mivot_viewer.instance
    # and feed it with the table row
    read = []
    for rec in table.array:
        mivot_object.update(rec)
        read.append(mivot_object.longitude.value)
        assert rec["RAICRS"] == mivot_object.longitude.value
        assert rec["DEICRS"] == mivot_object.latitude.value

if __name__ == '__main__':
    pytest.main()
