"""
Created on 13 Feb 2025

@author: laurentmichel
"""

__all__ = ["Url", "IvoaType", "Roles", "ModelPrefix", "VodmlUrl"]


class Url:
    # Filter profile service URL
    FPS = (
        "http://svo2.cab.inta-csic.es/svo/theory/fps/fpsmivot.php?PhotCalID="
    )

class IvoaType:
    string = "ivoa:string"
    real = "ivoa:real"
    RealQuantity = "ivoa:RealQuantity"
    bool = "ivoa:bool"

# accepted roles for all implemented classes
# Accepted roles correspond to the last element
# of the dmroles as defined in VODML
class Roles:
    EpochPosition = [
        "longitude",
        "latitude",
        "parallax",
        "radialVelocity",
        "pmLongitude",
        "pmLatitude",
        "epoch",
    ]
    EpochPositionCorrelations = [
        "longitudeParallax",
        "latitudeParallax",
        "pmLongitudeParallax",
        "pmlatitudeParallax",
        "longitudeLatitude",
        "pmLongitudePmLatitude",
        "latitudePmLatitude",
        "latitudePmLongitude",
        "longitudePmLatitude",
        "longitudePmLongitude",
        "isCovariance",
    ]
    PropertyError = [
        "parallax",
        "radialVelocity",
        "position",
        "properMotion",
    ]
    Symmetrical1D = [
        "sigma"
    ]
    Asymmetrical1D = [
        "low",
        "high"
    ]
    Symmetrical2D = [
        "sigma1",
        "sigma2"
    ]
    PhotometricProperty = ["value", "error"]
    Color = ["value", "error", "definition"]


# model named as defined in VODML
class ModelPrefix:
    ivoa = "ivoa"
    mango = "mango"
    Phot = "Phot"
    coords = "coords"
    meas = "meas"
    
# VODML urls for the supported models
# The keys match `ModelPrefix`
class VodmlUrl:
    ivoa = "https://www.ivoa.net/xml/VODML/IVOA-v1.vo-dml.xml"
    mango = "https://raw.githubusercontent.com/lmichel/MANGO/refs/heads/draft-0.1/vo-dml/desc.mango.vo-dml.xml"
    Phot = "https://ivoa.net/xml/VODML/Phot-v1.vodml.xml"
    coords = "https://ivoa.net/xml/VODML/Coords-v1.vo-dml.xml"
    meas = "https://ivoa.net/xml/VODML/Meas-v1.vo-dml.xml"

