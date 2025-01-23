'''
Created on 22 Jan 2025

@author: laurentmichel
'''
from astropy.io.votable import parse
from pyvo.utils import activate_features


from pyvo.mivot.writer.annotations import MivotAnnotations
from pyvo.mivot.utils.xml_utils import XmlUtils

activate_features("MIVOT")

def f1(a1="a1", b1="b1", c1="c1"):
    print(f"{a1} {b1} {c1}")
    
def f2(a2="a2", b2="b2", c2="c2"):
    print(f"{a2} {b2} {c2}")
    
def fa(args1={}, args2=[]):
    f1(**args1)
    f2(*args2)
    
if __name__ == '__main__':
    votable = parse("/Users/laurentmichel/Documents/seafile/Seafile/workspaces/git/pyvo/pyvo/mivot/tests/data/gaia_epoch_propagation_nomivot.xml")

    table = votable.get_first_table()   
    annottaion = MivotAnnotations()
    annottaion.add_mango_epoch_position(table,
                                        space_frame={"ref_frame": "ICRS"},
                                        time_frame={"ref_frame": "TCB"},
                                        sky_position={"longitude": "_RAJ2000", "latitude": "_DEJ2000",
                                                      "pmLongitude": "pmRA", "pmLatitude": "pmDE",
                                                      "parallax": "Plx", "radialVelocity": "RV"},
                                        correlations={"isCovariance": "*true", 
                                                      "longitudeLatitude": "RADEcor",
                                                      "latitudePmLongitude": "DEpmRAcor",  "latitudePmLatitude": "DEpmDEcor",
                                                      "longitudePmLongitude": "RApmRAcor",  "longitudePmLatitude": "RApmDEcor",
                                                      "longitudeParallax": "RAPlxcor", "latitudeParallax": "DEPlxcor", 
                                                      "pmLongitudeParallax": "PlxpmRAcor", "pmLatitudeParallax": "PlxpmDEcor", 
                                                      },
                                        errors={"parallax": "e_Plx", "radialVelocity": "e_RV",
                                                "position": {"class": "ErrorCorrMatrix", "columns": ["e_RA_ICRS", "e_RA_ICRS"]},
                                                "properMotion": {"class": "ErrorCorrMatrix", "columns": ["e_pmRA", "e_pmDE"]},                                            
                                                })
    
    annottaion.add_mango_magnitude(table, filter_name="GAIA/GAIA3.Grvs/AB", mag={"value": "GRVSmag"})
    annottaion.build_mivot_block()
    annottaion.insert_into_votable(votable, override=True)
    votable.to_xml('/Users/laurentmichel/Documents/seafile/Seafile/workspaces/git/pyvo/pyvo/mivot/tests/data/output.xml')
    XmlUtils.pretty_print(annottaion.mivot_block)
    