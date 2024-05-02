'''
Test the class generation from a dict.x
Created on 19 févr. 2024

@author: michel
'''
import pytest
from astropy.table import Table
from pyvo.mivot.viewer.mivot_instance import MivotInstance


fake_hk_dict = {
    "dmtype": "EpochPosition",
            "longitude": {
                "dmtype": "RealQuantity",
                "value": 52.2340018,
                "unit": "deg",
                "astropy_unit": {},
                "ref": "RAICRS"
            },
            "latitude": {
                "dmtype": "RealQuantity",
                "value": 59.8937333,
                "unit": "deg",
                "astropy_unit": {},
                "ref": "DEICRS"
            }
}

fake_dict = {
    "dmtype": "EpochPosition",
            "longitude": {
                "value": 52.2340018,
                "unit": "deg",
            },
            "latitude": {
                "value": 59.8937333,
                "unit": "deg",
            }
}


def test_mivot_instance_constructor():
    """Test the class generation from a dict."""
    mivot_object = MivotInstance(**fake_hk_dict)
    assert mivot_object.longitude.value == 52.2340018
    assert mivot_object.longitude.unit == "deg"
    assert mivot_object.latitude.value == 59.8937333
    assert mivot_object.latitude.unit == "deg"
    assert mivot_object.longitude.dmtype == "RealQuantity"
    assert mivot_object.dmtype == "EpochPosition"


def test_mivot_instance_update():
    """Test the class generation from a dict followed by an update"""
    mivot_object = MivotInstance(**fake_hk_dict)

    t = Table()
    t["RAICRS"] = [67.87]
    t["DEICRS"] = [-89.87]
    mivot_object.update(t[0])
    assert mivot_object.longitude.value == 67.87
    assert mivot_object.latitude.value == -89.87


def test_mivot_instance_update_wrong_columns():
    """Test the class generation from a dict followed by an update with wrong columns."""
    mivot_object = MivotInstance(**fake_hk_dict)

    t = Table()
    t["RAICRSXX"] = [67.87]
    t["DEICRS"] = [-89.87]
    with pytest.raises(KeyError, match="RAICRS"):
        mivot_object.update(t[0])


def test_mivot_instance_display_dict():
    """Test the class generation from a dict and rebuild the dict from the instance."""
    mivot_object = MivotInstance(**fake_hk_dict)
    assert mivot_object.hk_dict == fake_hk_dict
    assert mivot_object.dict == fake_dict
