"""
Check the API exposed to the user works properly
This unit test can also be used as a code example
Created on 26 Feb. 2024
@author: michel
"""

import os
import pytest
from urllib.request import urlretrieve
import astropy.units as u
from astropy.coordinates import SkyCoord
from pyvo.dal.scs import SCSService
from pyvo.mivot.version_checker import check_astropy_version
from pyvo.mivot import MivotViewer
from astropy.io.votable import parse


@pytest.fixture
def data_path():
    return os.path.dirname(os.path.realpath(__file__))


@pytest.fixture
def data_sample_url():
    return "https://raw.githubusercontent.com/ivoa/dm-usecases/main/pyvo-ci-sample/"


@pytest.fixture
def vizier_url():
    return "https://cdsarc.cds.unistra.fr/beta/viz-bin/mivotconesearch/I/239/hip_main"


@pytest.fixture
def delt_coo():
    """acceptable delta for coordinate value comparisons"""
    return 0.0000001


@pytest.fixture
def path_to_votable(data_path, data_sample_url):

    votable_name = "vizier_for_user_api.xml"
    votable_path = os.path.join(data_path, "data", votable_name)
    urlretrieve(data_sample_url + votable_name, votable_path)

    yield votable_path
    os.remove(votable_path)


@pytest.mark.remote_data
@pytest.mark.skipif(not check_astropy_version(), reason="need astropy 6+")
def test_mivot_viewer_next(path_to_votable):
    mivot_viewer = MivotViewer(path_to_votable)
    mivot_instance = mivot_viewer.dm_instance
    assert mivot_instance.dmtype == "EpochPosition"
    assert mivot_instance.Coordinate_coordSys.spaceRefFrame.value == "ICRS"
    ra = []
    dec = []
    while mivot_viewer.next():
        ra.append(mivot_instance.latitude.value)
        dec.append(mivot_instance.longitude.value)
    assert ra == [
        -0.36042119,
        0.22293899,
        -0.07592034,
        -0.21749947,
        -0.1281483,
        -0.28005255,
    ]
    assert dec == [
        0.04827189,
        0.16283175,
        0.29222255,
        0.42674592,
        359.5190115,
        359.94372764,
    ]


@pytest.mark.remote_data
@pytest.mark.skipif(not check_astropy_version(), reason="need astropy 6+")
def test_mivot_tablerow_next(path_to_votable):

    votable = parse(path_to_votable)
    table = votable.resources[0].tables[0]
    mivot_viewer = MivotViewer(votable)

    mivot_instance = mivot_viewer.dm_instance
    assert mivot_instance.dmtype == "EpochPosition"
    assert mivot_instance.Coordinate_coordSys.spaceRefFrame.value == "ICRS"
    ra = []
    dec = []
    for rec in table.array:
        mivot_instance.update(rec)
        ra.append(mivot_instance.latitude.value)
        dec.append(mivot_instance.longitude.value)
    assert ra == [
        -0.36042119,
        0.22293899,
        -0.07592034,
        -0.21749947,
        -0.1281483,
        -0.28005255,
    ]
    assert dec == [
        0.04827189,
        0.16283175,
        0.29222255,
        0.42674592,
        359.5190115,
        359.94372764,
    ]


@pytest.mark.remote_data
@pytest.mark.skipif(not check_astropy_version(), reason="need astropy 6+")
def test_with_with(path_to_votable):
    """check that the mivot object attribute are correct"""

    ref = [-0.36042119, 0.22293899, -0.07592034, -0.21749947, -0.1281483, -0.28005255]
    read = []
    with MivotViewer(path_to_votable) as mivot_viewer:
        mivot_object = mivot_viewer.dm_instance
        while mivot_viewer.next():
            read.append(mivot_object.latitude.value)

    assert read == ref


@pytest.mark.remote_data
@pytest.mark.skipif(not check_astropy_version(), reason="need astropy 6+")
def test_with_dict(path_to_votable):
    """check that the mivot object user dictionary"""

    with MivotViewer(path_to_votable) as mivot_viewer:
        mivot_object = mivot_viewer.dm_instance
        # jump to the last row
        while mivot_viewer.next():
            pass

    # check the slim (user friendly) dictionary
    assert mivot_object.dict == {
        "dmtype": "EpochPosition",
        "longitude": {"value": 359.94372764, "unit": "deg"},
        "latitude": {"value": -0.28005255, "unit": "deg"},
        "pmLongitude": {"value": -5.14, "unit": "mas/yr"},
        "pmLatitude": {"value": -25.43, "unit": "mas/yr"},
        "epoch": {"value": 1991.25, "unit": "year"},
        "Coordinate_coordSys": {
            "dmtype": "SpaceSys",
            "dmid": "SpaceFrame_ICRS",
            "dmrole": "coordSys",
            "spaceRefFrame": {"value": "ICRS"},
        },
    }
    # check the whole dictionary
    assert mivot_object.hk_dict == {
        "dmtype": "EpochPosition",
        "longitude": {"dmtype": "RealQuantity", "value": 359.94372764,
                      "unit": "deg", "astropy_unit": {}, "ref": "RAICRS"},
        "latitude": {"dmtype": "RealQuantity", "value": -0.28005255,
                     "unit": "deg", "astropy_unit": {}, "ref": "DEICRS"},
        "pmLongitude": {"value": -5.14, "unit": "mas/yr", "dmtype": "RealQuantity",
                        "ref": "pmRA", "astropy_unit": {}},
        "pmLatitude": {"value": -25.43, "unit": "mas/yr", "dmtype": "RealQuantity",
                       "ref": "pmDE", "astropy_unit": {}},
        "epoch": {"dmtype": "RealQuantity", "ref": None, "unit": "year", "value": 1991.25},
        "Coordinate_coordSys": {
            "dmtype": "SpaceSys",
            "dmid": "SpaceFrame_ICRS",
            "dmrole": "coordSys",
            "spaceRefFrame": {"dmtype": "SpaceFrame", "ref": None, "unit": None, "value": "ICRS"},
        },
    }


@pytest.mark.remote_data
@pytest.mark.skipif(not check_astropy_version(), reason="need astropy 6+")
def test_external_iterator(path_to_votable, delt_coo):
    """Checks the the values returned by MIVOT are
    the same as those read by Astropy
    """
    # parse the VOTable outside of the viewer
    votable = parse(path_to_votable)
    table = votable.resources[0].tables[0]
    # init the viewer
    mivot_viewer = MivotViewer(votable)
    mivot_object = mivot_viewer.dm_instance
    # and feed it with the table row
    read = []
    for rec in table.array:
        mivot_object.update(rec)
        read.append(mivot_object.longitude.value)
        assert rec["RAICRS"] == mivot_object.longitude.value
        assert rec["DEICRS"] == mivot_object.latitude.value


@pytest.mark.remote_data
@pytest.mark.skipif(not check_astropy_version(), reason="need astropy 6+")
def test_cone_search(vizier_url):
    scs_srv = SCSService(vizier_url)
    m_viewer = MivotViewer(
        scs_srv.search(
            pos=SkyCoord(ra=52.26708 * u.degree, dec=59.94027 * u.degree, frame="icrs"),
            radius=0.05,
        )
    )
    mivot_instance = m_viewer.dm_instance
    assert mivot_instance.dmtype == "EpochPosition"
    assert mivot_instance.Coordinate_coordSys.spaceRefFrame.value == "ICRS"
    ra = []
    dec = []
    while m_viewer.next():
        ra.append(mivot_instance.latitude.value)
        dec.append(mivot_instance.longitude.value)
    assert ra == [59.94033461]
    assert dec == [52.26722684]


if __name__ == "__main__":
    pytest.main()
