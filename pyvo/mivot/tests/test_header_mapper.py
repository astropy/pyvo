"""
This module contains test cases for validating the generation of mapping dictionaries that allow
to extract Mivot instances from INFO located in the VOTable header
"""
import pytest
from astropy.io.votable import parse
from astropy.utils.data import get_pkg_data_filename
from pyvo.utils import activate_features

from pyvo.mivot.version_checker import check_astropy_version
from pyvo.mivot.writer.header_mapper import HeaderMapper

# Enable MIVOT-specific features in the pyvo library
activate_features("MIVOT")

data_origin_mapping = {
    "service_protocol":
    "ivo://ivoa.net/std/ConeSearch/v1.03",
    "request_date":
    "2025-04-07T12:06:32",
    "request": ("https://cdsarc.cds.unistra.fr/beta/viz-bin/mivotconesearch"
                "/I/329/urat1?RA=52.26708&DEC=59.94027&SR=0.05"),
    "contact":
    "cds-question@unistra.fr",
    "server_software":
    "7.4.6",
    "publisher":
    "CDS",
    "dataOrigin": [{
        "ivoid": "ivo://cds.vizier/i/329",
        "creators": ["Zacharias N."],
        "cites": "bibcode:2015AJ....150..101Z",
        "original_date": "2015",
        "reference_url": "https://cdsarc.cds.unistra.fr/viz-bin/cat/I/329",
        "rights_uri": "https://cds.unistra.fr/vizier-org/licences_vizier.html",
        "articles": [{
            "editor": "Astronomical Journal (AAS)"
        }]
    }]
}

coosys_mappings = [{"spaceRefFrame": "ICRS", "epoch": "2345"}]
timesys_mappings = [{"timescale": "TCB"}]


@pytest.mark.skipif(not check_astropy_version(), reason="need astropy 6+")
def test_all():
    """
    checks that the mapping dictionaries extracte from the VOTable match the expected ones
    """
    votable = parse(get_pkg_data_filename("data/test.header_extraction.xml"))

    builder = HeaderMapper(votable)
    assert builder.extract_origin_mapping() == data_origin_mapping

    assert builder.extract_coosys_mapping() == coosys_mappings
    assert builder.extract_timesys_mapping() == timesys_mappings


@pytest.mark.skipif(not check_astropy_version(), reason="need astropy 6+")
def test_field_extraction():
    """
    checks that the epochPosition mapping dictionaries extracted from
    the VOTable columns match the expected ones
    """
    votable = parse(get_pkg_data_filename("data/test.header_extraction.1.xml"))
    builder = HeaderMapper(votable)
    mapping, error_mapping = builder.extract_epochposition_mapping()
    assert mapping == {"longitude": "RA_ICRS", "latitude": "DE_ICRS", "parallax": "Plx",
                       "pmLongitude": "pmRA", "pmLatitude": "pmDE", "radialVelocity": "RV"}
    assert error_mapping == {"position": {"class": "PErrorSym2D",
                                          "sigma1": "e_RA_ICRS", "sigma2": "e_DE_ICRS"},
                             "parallax": {"class": "PErrorSym1D", "sigma": "e_Plx"},
                             "properMotion": {"class": "PErrorSym2D",
                                              "sigma1": "e_pmRA", "sigma2": "e_pmDE"},
                             "radialVelocity": {"class": "PErrorSym1D", "sigma": "e_RV"}}

    votable = parse(get_pkg_data_filename("data/test.header_extraction.2.xml"))
    builder = HeaderMapper(votable)
    mapping, error_mapping = builder.extract_epochposition_mapping()
    assert mapping == {"obsDate": {"dateTime": "ObsDate",
                                    "representation": "iso"},
                        "longitude": "RAB1950",
                        "latitude": "DEB1950"
                     }
