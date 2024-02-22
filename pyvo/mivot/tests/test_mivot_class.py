'''
Test the class generation from a dict.x
Created on 19 févr. 2024

@author: michel
'''
from pyvo.mivot.viewer.mivot_instance import MivotInstance
from pyvo.utils.prototype import activate_features

activate_features('MIVOT')

faze_dict = {
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
  },
  }

def test_mivot_viewer_constructor():
    """Test the class generation from a dict."""
    mivot_object = MivotInstance(**faze_dict)    
    assert mivot_object.longitude.value == 52.2340018
    assert mivot_object.longitude.unit == "deg"
    assert mivot_object.longitude.dmtype == "RealQuantity"
    assert mivot_object.dmtype == "EpochPosition"


