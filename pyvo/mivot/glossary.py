"""
Glossary for the MIVOT package

- Model related words (hard-coded for now)
- URLs
"""

__all__ = ["Url", "IvoaType", "Roles", "CoordSystems", "ModelPrefix",
           "VodmlUrl", "EpochPositionAutoMapping"]


class Url:
    """
    Service URL(s) that are used by the API
    """
    #: Filter Profile Service URL (SVO)
    FPS = (
        "http://svo2.cab.inta-csic.es/svo/theory/fps/fpsmivot.php?PhotCalID="
    )


class IvoaType:
    """
    Primitive VODML types
    """
    #: primitive type for strings
    string = "ivoa:string"
    #: primitive type for reals
    real = "ivoa:real"
    #: primitive type for real quantity (real + unit)
    RealQuantity = "ivoa:RealQuantity"
    #: primitive type for booleans
    bool = "ivoa:boolean"
    #: primitive type for a point in time
    datetime = "ivoa:datatime"


class Roles:
    """
    Accepted roles for all implemented classes;
    correspond to the last path element of the ``dmroles``
    as defined in VODML (VODML-ID)
    """
    #: Roles of the EpochPosition class that are supported
    EpochPosition = [
        "longitude",
        "latitude",
        "parallax",
        "radialVelocity",
        "pmLongitude",
        "pmLatitude",
        "obsDate",
    ]
    #: Roles of the EpochPositionCorrelations class that are supported
    EpochPositionCorrelations = [
        "longitudeParallax",
        "latitudeParallax",
        "pmLongitudeParallax",
        "pmLatitudeParallax",
        "longitudeLatitude",
        "pmLongitudePmLatitude",
        "latitudePmLatitude",
        "latitudePmLongitude",
        "longitudePmLatitude",
        "longitudePmLongitude",
        "isCovariance",
    ]
    #: Roles of the EpochPositionErrors class that are supported
    EpochPositionErrors = [
        "parallax",
        "radialVelocity",
        "position",
        "properMotion",
    ]
    #: Roles of the PErrorSym1D class that is supported
    PErrorSym1D = [
        "sigma"
    ]
    #: Roles of the PErrorAsym1D class that are supported
    PErrorAsym1D = [
        "low",
        "high"
    ]
    #: Roles of the PErrorSym2D class that are supported
    PErrorSym2D = [
        "sigma1",
        "sigma2"
    ]
    #: Roles of the PErrorSym2D class that are supported
    PErrorEllipse = [
        "semiMajorAxis",
        "semiMinorAxis",
        "angle"
    ]
    #: Roles of the PhotometricProperty class that are supported
    PhotometricProperty = ["value",
                           "error"
    ]
    #: Roles of the Color class that are supported
    Color = ["value",
             "error",
             "definition"
    ]
    #: Roles of the QueryOrigin class that are supported
    QueryOrigin = ["publisher", "server_software", "service_protocol",
                   "request", "request_date", "query", "contact", "ivoid"
    ]
    #: Roles of the DataOrigin class that are supported
    DataOrigin = ["ivoid", "reference_url", "resource_version", "creators",
                  "cites", "is_derived_from", "original_date", "rights", "rights_uri", "articles"
    ]
    #: Roles of the Article class that are supported
    Article = ["identifier", "editor"
    ]


class CoordSystems:
    """
    Supported values for the coordinate system parameters (space and time)
    """
    #: see  IVOA  `refframe <https://www.ivoa.net/rdf/refframe/2022-02-22/refframe.html>`_ vocabulary
    space_frames = ["eq_FK4", "FK4", "eq_FK5", "FK5", "ICRS", "GALACTIC", "SUPER_GALACTIC", "ECLIPTIC"]
    #: see  IVOA  `refposition <https://www.ivoa.net/rdf/refposition/2019-03-15/refposition.html>`_ vocabulary
    ref_positions = ["BARYCENTER", "GEOCENTER", "TOPOCENTER"]
    #: see  IVOA  `timescale <https://www.ivoa.net/rdf/timescale/2019-03-15/timescale.html>`_ vocabulary
    time_frames = ["TAI", "TT", "TDT", "ET", "IAT", "UT1",
                   "UTC", "GMT", "GPS", "TCG", "TCB", "TBD", "LOCAL"]
    #: supported time formats (could be replaced witha vocabulary later on)
    time_formats = ["byear", "cxcsec", "decimalyear", "fits",
                    "gps", "iso", "timestamp", "jyear", "year", "jd", "mjd"]


class ModelPrefix:
    """
    Model names as defined in VODML
    """
    #: `VODML <https://www.ivoa.net/documents/VODML/20180910/index.html>`_ primitive types
    ivoa = "ivoa"
    #: VODML prefix of the MANGO model
    mango = "mango"
    #: VODML prefix of the `Photometry Data Model
    #: <https://www.ivoa.net/documents/PHOTDM/20221101/index.html>`_
    Phot = "Phot"
    #: VODML prefix of the Astronomical `Astronomical Coordinates and Coordinate Systems
    #: <https://www.ivoa.net/documents/Coords/20221004/index.html>`_ datamodel
    coords = "coords"
    #: VODML prefix of the `Astronomical Measurements Model
    #: <https://www.ivoa.net/documents/Meas/20221004/index.html>`_
    meas = "meas"


class VodmlUrl:
    """
    VODML URLs of the supported models.
    Names of the class attributes match the `ModelPrefix` fields.
    """
    #: VODML URL of the `VODML
    #: <https://www.ivoa.net/documents/VODML/20180910/index.html>`_ primitive types
    ivoa = "https://www.ivoa.net/xml/VODML/IVOA-v1.vo-dml.xml"
    #: VODML URL of the MANGO model
    mango = "https://raw.githubusercontent.com/ivoa-std/MANGO/refs/heads/wd-v1.0/vo-dml/mango.vo-dml.xml"
    #: VODML URL of the  `Photometry Data Model <https://www.ivoa.net/documents/PHOTDM/20221101/index.html>`_
    Phot = "https://ivoa.net/xml/VODML/Phot-v1.vodml.xml"
    #: VODML URL of the `Astronomical Coordinates and Coordinate Systems
    #: <https://www.ivoa.net/documents/Coords/20221004/index.html>`_  datamodel
    coords = "https://ivoa.net/xml/VODML/Coords-v1.vo-dml.xml"
    #: VODML URL of the `Astronomical Measurements Model
    #: <https://www.ivoa.net/documents/Meas/20221004/index.html>`_
    meas = "https://ivoa.net/xml/VODML/Meas-v1.vo-dml.xml"


class EpochPositionAutoMapping:
    """
    Expected UCDs for identifying FIELD to be mapped to EpochPosition attributes.

    - UCD-s of the associated errors are derived from them
    - list items must have an exact match
    - Single values are evaluated as starting with
    """
    #: UCD-s accepted to map the longitude
    longitude = ["POS_EQ_RA_MAIN", "pos.eq.ra;meta.main"]
    #: UCD-s accepted to map the latitude
    latitude = ["POS_EQ_DEC_MAIN", "pos.eq.dec;meta.main"]
    #: UCD-s accepted to map the proper motion longitude
    pmLongitude = ["pos.pm;pos.eq.ra"]
    #: UCD-s accepted to map the proper motion latitude
    pmLatitude = ["pos.pm;pos.eq.dec"]
    #: UCD-s accepted to map the obsDate
    obsDate = ["time.epoch;obs;stat.mean", "time.epoch;obs"]
    #: UCD-s accepted to map the parallax
    parallax = ["pos.parallax.trig"]
    #: first word of UCD-s accepted to map the radial velocity
    radialVelocity = "spect.dopplerVeloc.opt"
