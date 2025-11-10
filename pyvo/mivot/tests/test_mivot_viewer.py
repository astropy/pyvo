# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Test for mivot.viewer.mivot_viewer.py
"""
import os
import pytest
import re
from astropy.utils.data import get_pkg_data_filename
from pyvo.mivot.utils.vocabulary import Constant
from pyvo.mivot.utils.dict_utils import DictUtils
from pyvo.mivot.utils.exceptions import MappingError
from pyvo.mivot.version_checker import check_astropy_version
from pyvo.mivot.viewer import MivotViewer
from astropy import version as astropy_version

dm_raw_instances = [
    {
        "dmrole": "",
        "dmtype": "mango:Brightness",
        "value": {
            "dmtype": "ivoa:RealQuantity",
            "value": None,
            "unit": None,
            "ref": "SC_EP_1_FLUX",
        },
    },
    {
        "dmrole": "",
        "dmtype": "mango:Brightness",
        "value": {
            "dmtype": "ivoa:RealQuantity",
            "value": None,
            "unit": None,
            "ref": "SC_EP_2_FLUX",
        },
    },
    {
        "dmrole": "",
        "dmtype": "mango:Brightness",
        "value": {
            "dmtype": "ivoa:RealQuantity",
            "value": None,
            "unit": None,
            "ref": "SC_EP_3_FLUX",
        },
    },
]

globals_photcal = {
    "dmid": "CoordSystem_XMM_EB1_id",
    "dmtype": "Phot:PhotCal",
    "identifier": {
        "dmtype": "ivoa:string",
        "value": "XMM/EPIC/EB1",
        "unit": None,
        "ref": None,
    },
    "magnitudeSystem": {
        "dmrole": "Phot:PhotCal.magnitudeSystem",
        "dmtype": "Phot:MagnitudeSystem",
        "type": {
            "dmtype": "Phot:TypeOfMagSystem",
            "value": "XMM",
            "unit": None,
            "ref": None,
        },
        "referenceSpectrum": {
            "dmtype": "ivoa:anyURI",
            "value": "https://xmm-tools.cosmos.esa.int/external"
                     "/xmm_user_support/documentation/sas_usg/USG/SASUSG.html",
            "unit": None,
            "ref": None,
        },
    },
    "photometryFilter": {
        "dmid": "CoordSystem_XMM_FILTER_EB1_id",
        "dmtype": "Phot:PhotometryFilter",
        "dmrole": "Phot:PhotCal.photometryFilter",
        "identifier": {
            "dmtype": "ivoa:string",
            "value": "XMM/EPIC/EB1",
            "unit": None,
            "ref": None,
        },
        "name": {
            "dmtype": "ivoa:string",
            "value": "XMM EPIC EB1",
            "unit": None,
            "ref": None,
        },
        "description": {
            "dmtype": "ivoa:string",
            "value": "Soft",
            "unit": None,
            "ref": None,
        },
        "bandName": {
            "dmtype": "ivoa:string",
            "value": "EB1",
            "unit": None,
            "ref": None,
        },
        "spectralLocation": {
            "dmrole": "Phot:PhotometryFilter.spectralLocation",
            "dmtype": "Phot:SpectralLocation",
            "ucd": {
                "dmtype": "Phot:UCD",
                "value": "em.wl.effective",
                "unit": None,
                "ref": None,
            },
            "unitexpression": {
                "dmtype": "ivoa:Unit",
                "value": "keV",
                "unit": None,
                "ref": None,
            },
            "value": {"dmtype": "ivoa:real", "value": 0.35, "unit": None, "ref": None},
        },
        "bandwidth": {
            "dmrole": "Phot:PhotometryFilter.bandwidth",
            "dmtype": "Phot:Bandwidth",
            "ucd": {
                "dmtype": "Phot:UCD",
                "value": "instr.bandwidth;stat.fwhm",
                "unit": None,
                "ref": None,
            },
            "unitexpression": {
                "dmtype": "ivoa:Unit",
                "value": "keV",
                "unit": None,
                "ref": None,
            },
            "extent": {"dmtype": "ivoa:real", "value": 0.3, "unit": None, "ref": None},
            "start": {"dmtype": "ivoa:real", "value": 0.2, "unit": None, "ref": None},
            "stop": {"dmtype": "ivoa:real", "value": 0.5, "unit": None, "ref": None},
        },
        "transmissionCurve": {
            "dmrole": "Phot:PhotometryFilter.transmissionCurve",
            "dmtype": "Phot:TransmissionCurve",
            "access": {
                "dmrole": "Phot:TransmissionCurve.access",
                "dmtype": "Phot:Access",
                "reference": {
                    "dmtype": "ivoa:anyURI",
                    "value": "https://xmm-tools.cosmos.esa.int/external/xmm_user_support"
                             "/documentation/sas_usg/USG/SASUSG.html",
                    "unit": None,
                    "ref": None,
                },
                "format": {
                    "dmtype": "ivoa:string",
                    "value": "text/html",
                    "unit": None,
                    "ref": None,
                },
            },
        },
    },
}


@pytest.mark.skipif(not check_astropy_version(), reason="need astropy 6+")
def test_get_first_instance_dmtype(path_to_first_instance):
    """
    Test the function get_first_instance_dmtype() which is
    used to find the first INSTANCE/COLLECTION in TEMPLATES.
    """
    m_viewer = MivotViewer(votable_path=path_to_first_instance)
    assert m_viewer.get_dm_instance_dmtypes("one_instance")[0] == "one_instance"
    assert m_viewer.get_dm_instance_dmtypes("some_instances")[0] == "first"

    with pytest.raises(Exception, match="Can't find INSTANCE in TEMPLATES"):
        m_viewer.get_dm_instance_dmtypes("empty")

    with pytest.raises(Exception, match="No TEMPLATES with tableref=not_existing_tableref"):
        m_viewer.get_dm_instance_dmtypes("not_existing_tableref")


@pytest.mark.skipif(not check_astropy_version(), reason="need astropy 6+")
def test_table_ref(m_viewer):
    """
    Test if the mivot_viewer can find each table_ref and connect to the right table_ref.
    Test if the mivot_viewer can find each models.
    """
    assert m_viewer._mapped_tables == ['_PKTable', 'Results']
    with pytest.raises(Exception,
                       match=re.escape(r"The table first_table doesn't match with any mapped_table "
                                       r"(['_PKTable', 'Results']) encountered in TEMPLATES")):
        m_viewer._connect_table("wrong_tableref")
    assert m_viewer.connected_table_ref == Constant.FIRST_TABLE
    assert (m_viewer.get_models()
            == {'mango': 'file:/Users/sao/Documents/IVOA/GitHub/ivoa-dm-examples/tmp/Mango-v1.0.vo-dml.xml',
                'cube': 'https://volute.g-vo.org/svn/trunk/projects/dm/Cube/vo-dml/Cube-1.0.vo-dml.xml',
                'ds': 'https://volute.g-vo.org/svn/trunk/projects/dm/'
                      'DatasetMetadata/vo-dml/DatasetMetadata-1.0.vo-dml.xml',
                'meas': 'https://www.ivoa.net/xml/Meas/20200908/Meas-v1.0.vo-dml.xml',
                'coords': 'https://www.ivoa.net/xml/STC/20200908/Coords-v1.0.vo-dml.xml',
                'ivoa': 'https://www.ivoa.net/xml/VODML/IVOA-v1.vo-dml.xml'})


@pytest.mark.skipif(not check_astropy_version(), reason="need astropy 6+")
def test_global_getters(m_viewer):
    """
    Test each getter for TEMPLATES of the model_viewer.
    """
    assert m_viewer.get_table_ids() == ['_PKTable', 'Results']
    assert m_viewer.get_models() == DictUtils.read_dict_from_file(
        get_pkg_data_filename("data/reference/globals_models.json"))

    m_viewer._connect_table('_PKTable')
    row = m_viewer.next_table_row()
    assert row[0] == '5813181197970338560'
    assert row[1] == 'G'
    row = m_viewer.next_table_row()
    assert row[0] == '5813181197970338560'
    assert row[1] == 'BP'
    m_viewer.rewind()
    row = m_viewer.next_table_row()
    assert row[0] == '5813181197970338560'
    assert row[1] == 'G'


@pytest.mark.skipif(not check_astropy_version(), reason="need astropy 6+")
def test_no_mivot(path_no_mivot):
    """
    Test the viewer behavior when there is no mapping
    """
    m_viewer = MivotViewer(path_no_mivot)
    assert m_viewer.get_table_ids() is None
    assert m_viewer.get_models() is None

    with pytest.raises(MappingError):
        m_viewer._connect_table('_PKTable')
    with pytest.raises(MappingError):
        m_viewer._connect_table()

    assert m_viewer.next_table_row() is None


@pytest.mark.skipif(not check_astropy_version(), reason="need astropy 6+")
def test_instance_mutiple_in_templates(path_to_multiple_instance):
    """
    Test case with a TEMPLATES containing multiple instances
    """
    m_viewer = MivotViewer(votable_path=path_to_multiple_instance)
    instance_dict = []
    # test the DM instances children of TEMPLATES before their values are set
    for dmi in m_viewer.dm_instances:
        instance_dict.append(dmi.to_hk_dict())
    assert instance_dict == dm_raw_instances

    # test the DM instances children of TEMPLATES set with the values of the first row
    m_viewer.next_row_view()
    row_values = []
    for dmi in m_viewer.dm_instances:
        row_values.append(dmi.value.value)
    assert row_values == pytest.approx([0.0, 0.1, 0.2], rel=1e-3)

    # test the DM instances children of TEMPLATES set with the values of the second row
    m_viewer.next_row_view()
    row_values = []
    for dmi in m_viewer.dm_instances:
        row_values.append(dmi.value.value)
    assert row_values == pytest.approx([1.0, 2.1, 3.2], rel=1e-3)


@pytest.mark.skipif(not check_astropy_version(), reason="need astropy 6+")
def test_globals_instances(path_to_multiple_instance):
    """
    Test case for the GLOBALS instance access as MivotInstances
    """
    m_viewer = MivotViewer(votable_path=path_to_multiple_instance)
    instance_dict = []
    photcals = 0
    photfilters = 0
    # test the DM instances children of TEMPLATES before their values are set
    for dmi in m_viewer.dm_globals_instances:
        if dmi.dmtype == "Phot:PhotCal":
            photcals += 1
        elif dmi.dmtype == "Phot:PhotometryFilter":
            photfilters += 1
        else:
            assert False, f"Unexpected dmtype {dmi.dmtype} in GLOBALS "
        instance_dict.append(dmi.to_hk_dict())
    assert photcals == 3
    assert photfilters == 3
    # just check the first one
    assert instance_dict[0] == globals_photcal


def test_check_version(path_to_viewer):
    if not check_astropy_version():
        with pytest.raises(Exception,
                           match=f"Astropy version {astropy_version.version} "
                                 f"is below the required version 6.0 for the use of MIVOT."):
            MivotViewer(votable_path=path_to_viewer)
    if astropy_version.version is None:
        assert not check_astropy_version()
    elif astropy_version.version < '6.0':
        assert not check_astropy_version()
    else:
        assert check_astropy_version() is True


@pytest.fixture
def m_viewer():
    if not check_astropy_version():
        pytest.skip("MIVOT test skipped because of the astropy version.")

    votable_name = "test.mivot_viewer.xml"
    votable_path = get_pkg_data_filename(os.path.join("data", votable_name))
    return MivotViewer(votable_path=votable_path)


@pytest.fixture
def path_to_viewer():
    if not check_astropy_version():
        pytest.skip("MIVOT test skipped because of the astropy version.")

    votable_name = "test.mivot_viewer.xml"
    return get_pkg_data_filename(os.path.join("data", votable_name))


@pytest.fixture
def path_to_multiple_instance():

    votable_name = "test.instance_multiple.xml"
    return get_pkg_data_filename(os.path.join("data", votable_name))


@pytest.fixture
def path_to_first_instance():

    votable_name = "test.mivot_viewer.first_instance.xml"
    return get_pkg_data_filename(os.path.join("data", votable_name))


@pytest.fixture
def path_no_mivot():
    votable_name = "test.mivot_viewer.no_mivot.xml"
    return get_pkg_data_filename(os.path.join("data", votable_name))
