# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
This module contains test cases for validating the functionality of MivotInstance, MivotAnnotations,
and related components in the pyvo.mivot package. These tests ensure that the classes behave as
expected, including error handling and XML generation for data models.
"""

import os
import pytest
from unittest.mock import patch
from astropy.io.votable import parse
from astropy.utils.data import get_pkg_data_contents, get_pkg_data_filename
from pyvo.utils import activate_features

from pyvo.mivot.version_checker import check_astropy_version
from pyvo.mivot.utils.xml_utils import XmlUtils
from pyvo.mivot.writer.instances_from_models import InstancesFromModels


# Enable MIVOT-specific features in the pyvo library
activate_features("MIVOT")

# File paths for test data
votable_path = os.path.realpath(
    os.path.join(__file__, "..", "data", "test.mivot_viewer.no_mivot.xml")
)
data_path = os.path.realpath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")
)


@pytest.fixture()
def mocked_fps_grvs(mocker):

    def callback(request, context):
        return bytes(get_pkg_data_contents('data/filter_gaia_grvs.xml'), "utf8")
    with mocker.register_uri(
        'GET', 'http://svo2.cab.inta-csic.es/svo/theory/fps/fpsmivot.php?PhotCalID=GAIA/GAIA3.Grvs/AB',
        content=callback
    ) as matcher:
        yield matcher


@pytest.fixture()
def mocked_fps_grp(mocker):

    def callback(request, context):
        return bytes(get_pkg_data_contents('data/filter_gaia_grp.xml'), "utf8")
    with mocker.register_uri(
        'GET', 'http://svo2.cab.inta-csic.es/svo/theory/fps/fpsmivot.php?PhotCalID=GAIA/GAIA3.Grp/AB',
        content=callback
    ) as matcher:
        yield matcher


@pytest.fixture
def mocked_fps():
    with patch('requests.get') as mock_get:
        yield mock_get


@pytest.mark.filterwarnings("ignore:root:::")
def add_color(builder):

    filter_ids = {"high": "GAIA/GAIA3.Grp/AB", "low": "GAIA/GAIA3.Grvs/AB"}
    mapping = {"value": 8.76, "definition": "ColorIndex",
             "error": {"class": "PErrorAsym1D", "low": 1, "high": 3}
             }
    semantics = {"description": "very nice color", "uri": "vocabulary#term", "label": "term"}
    builder.add_mango_color(filter_ids=filter_ids, mapping=mapping, semantics=semantics)


@pytest.mark.filterwarnings("ignore:root:::")
def add_photometry(builder):
    photcal_id = "GAIA/GAIA3.Grvs/AB"
    mapping = {"value": "GRVSmag",
             "error": {"class": "PErrorAsym1D", "low": 1, "high": 3}
             }
    semantics = {"description": "Grvs magnitude",
               "uri": "https://www.ivoa.net/rdf/uat/2024-06-25/uat.html#magnitude",
               "label": "magnitude"}
    builder.add_mango_brightness(photcal_id=photcal_id, mapping=mapping, semantics=semantics)


def add_epoch_positon(builder):
    frames = {"spaceSys": {"spaceRefFrame": "ICRS", "refPosition": 'BARYCENTER', "equinox": None},
             "timeSys": {"timescale": "TCB", "refPosition": 'BARYCENTER'}}
    mapping = {"longitude": "_RAJ2000", "latitude": "_DEJ2000",
             "pmLongitude": "pmRA", "pmLatitude": "pmDE",
             "parallax": "Plx", "radialVelocity": "RV",
             "obsDate": {"representation": "mjd", "dateTime": 579887.6},
             "correlations": {"isCovariance": True,
                              "longitudeLatitude": "RADEcor",
                              "latitudePmLongitude": "DEpmRAcor", "latitudePmLatitude": "DEpmDEcor",
                              "longitudePmLongitude": "RApmRAcor", "longitudePmLatitude": "RApmDEcor",
                              "longitudeParallax": "RAPlxcor", "latitudeParallax": "DEPlxcor",
                              "pmLongitudeParallax": "PlxpmRAcor", "pmLatitudeParallax": "PlxpmDEcor",
                            },
             "errors": {"position": {"class": "PErrorSym2D", "sigma1": "e_RA_ICRS", "sigma2": "e_DE_ICRS"},
                         "properMotion": {"class": "PErrorSym2D", "sigma1": "e_pmRA", "sigma2": "e_pmDE"},
                         "parallax": {"class": "PErrorSym1D", "sigma": "e_Plx"},
                         "radialVelocity": {"class": "PErrorSym1D", "sigma": "e_RV"}
                        }
             }
    semantics = {"description": "6 parameters position",
                 "uri": "https://www.ivoa.net/rdf/uat/2024-06-25/uat.html#astronomical-location",
                 "label": "Astronomical location"}

    builder.add_mango_epoch_position(frames=frames, mapping=mapping, semantics=semantics)


@pytest.mark.usefixtures("mocked_fps_grvs", "mocked_fps_grp")
@pytest.mark.skipif(not check_astropy_version(), reason="need astropy 6+")
def test_all_properties():
    votable_filename = get_pkg_data_filename("data/test.mango_annoter.xml")

    votable = parse(votable_filename)
    builder = InstancesFromModels(votable, dmid="DR3Name")
    # pylint: disable=E501
    builder.add_query_origin(
        {"service_protocol": "ASU",
          "request_date": "2024-03-21T15:16:08",
          "request": ("https://vizier.cds.unistra.fr/viz-bin/votable?-oc.form=dec&amp;-out.max=5&amp;"
                      "-out.add=_r&amp;-out.add=_RAJ,_DEJ&amp;-sort=_r&amp;-c.eq=J2000&amp;-c.r=  2&amp;"
                      "-c.u=arcmin&amp;-c.geom=r&amp;-source=I/355/gaiadr3&amp;-order=I&amp;"
                      "-out.orig=standard&amp;-out=DR3Name&amp;-out=RA_ICRS&amp;-out=DE_ICRS&amp;"
                      "-out=Source&amp;-out=e_RA_ICRS&amp;-out=e_DE_ICRS&amp;-out=Plx&amp;"
                      "-out=e_Plx&amp;-out=PM&amp;-out=pmRA&amp;-out=e_pmRA&amp;-out=pmDE&amp;"
                      "-out=e_pmDE&amp;-out=RADEcor&amp;-out=RAPlxcor&amp;-out=RApmRAcor&amp;"
                      "-out=RApmDEcor&amp;-out=DEPlxcor&amp;-out=DEpmRAcor&amp;-out=DEpmDEcor&amp;"
                      "-out=PlxpmRAcor&amp;-out=PlxpmDEcor&amp;-out=pmRApmDEcor&amp;-out=RV&amp;"
                      "-out=e_RV&amp;-out=Vbroad&amp;-out=GRVSmag&amp;-out=QSO&amp;-out=Gal&amp;-out=NSS&amp;"
                      "-out=XPcont&amp;-out=XPsamp&amp;-out=RVS&amp;-out=EpochPh&amp;-out=EpochRV&amp;"
                      "-out=MCMCGSP&amp;-out=MCMCMSC&amp;-out=And&amp;-out=Teff&amp;-out=logg&amp;"
                      "-out=[Fe/H]&amp;-out=Dist&amp;-out=A0&amp;-out=HIP&amp;-out=PS1&amp;-out=SDSS13&amp;"
                      "-out=SKYM2&amp;-out=TYC2&amp;-out=URAT1&amp;-out=AllWISE&amp;-out=APASS9&amp;"
                      "-out=GSC23&amp;-out=RAVE5&amp;-out=2MASS&amp;-out=RAVE6&amp;-out=RAJ2000&amp;"
                      "-out=DEJ2000&amp;"),
          "contact": "cds-question@unistra.fr",
          "server_software": "7.33.3",
          "publisher": "CDS",
          "dataOrigin": [{"ivoid": "ivo://cds.vizier/i/355",
                         "creators": ["Gaia collaboration"],
                         "cites": "bibcode:2022yCat.1355....0G, ""doi:10.26093/cds/vizier.1355",
                         "original_date": "2022",
                         "reference_url": "https://cdsarc.cds.unistra.fr/viz-bin/cat/I/355",
                         "rights_uri": "https://cds.unistra.fr/vizier-org/licences_vizier.html",
                         "articles": [{"identifier": "doi:10.1051/0004-6361/202039657e]",
                                       "editor": "A&A"}]
                         }]
          })
    add_color(builder)
    add_photometry(builder)
    add_epoch_positon(builder)
    builder.pack_into_votable()
    XmlUtils.pretty_print(builder._annotation.mivot_block)
    assert XmlUtils.strip_xml(builder._annotation.mivot_block) == (
        XmlUtils.strip_xml(get_pkg_data_contents("data/reference/mango_object.xml"))
    )


@pytest.mark.skipif(not check_astropy_version(), reason="need astropy 6+")
def test_extraction_from_votable_header():
    """ test that the automatic mapping extraction is well connected with the annoter
    """
    votable_filename = get_pkg_data_filename("data/test.header_extraction.1.xml")

    votable = parse(votable_filename)
    builder = InstancesFromModels(votable, dmid="URAT1")
    builder.extract_frames()
    builder.extract_data_origin()
    epoch_position_mapping = builder.extract_epoch_position_parameters()
    builder.add_mango_epoch_position(**epoch_position_mapping)
    builder.pack_into_votable()
    assert XmlUtils.strip_xml(builder._annotation.mivot_block) == (
        XmlUtils.strip_xml(get_pkg_data_contents("data/reference/test_header_extraction.xml"))
    )
