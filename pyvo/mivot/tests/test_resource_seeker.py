# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Test for mivot.seekers.resource_seeker.py
"""
import os
import pytest
from urllib.request import urlretrieve
from astropy.io.votable import parse
from pyvo.mivot.seekers.resource_seeker import ResourceSeeker
from pyvo.mivot.version_checker import check_astropy_version
from pyvo.utils import activate_features

activate_features('MIVOT')


@pytest.fixture
def rseeker(data_path, data_sample_url):
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")

    votable_name = "test_ressource_seeker.xml"
    votable_path = os.path.join(data_path, "data", "input", votable_name)
    urlretrieve(data_sample_url + votable_name,
                votable_path)
    votable = parse(votable_path)
    for resource in votable.resources:
        yield ResourceSeeker(resource)
    os.remove(votable_path)


@pytest.fixture
def data_sample_url():
    return "https://raw.githubusercontent.com/ivoa/dm-usecases/main/pyvo-ci-sample/"


@pytest.mark.remote_data
def test_id_table(rseeker):
    """
    Checks the IDs of tables found by the RessourceSeeker,
    checks the IDs of the field of the table concerned.
    """
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")
    assert rseeker.get_table_ids() == ['_PKTable', 'Results']
    assert (rseeker.get_id_index_mapping('_PKTable')
            == {'pksrcid': {'ID': '_pksrcid', 'indx': 0},
                'pkband': {'ID': '_pkband', 'indx': 1}
                }
            )
    assert (rseeker.get_id_index_mapping('Results')
            == {'source_id': {'ID': '_srcid', 'indx': 0},
                'transit_id': {'ID': 'transit_id', 'indx': 1},
                'band': {'ID': '_band', 'indx': 2},
                'time': {'ID': '_obstime', 'indx': 3},
                'mag': {'ID': '_mag', 'indx': 4},
                'flux': {'ID': '_flux', 'indx': 5},
                'flux_error': {'ID': '_fluxerr', 'indx': 6},
                'flux_over_error': {'ID': 'flux_over_error', 'indx': 7},
                'rejected_by_photometry': {'ID': 'rejected_by_photometry', 'indx': 8},
                'rejected_by_variability': {'ID': 'rejected_by_variability', 'indx': 9},
                'other_flags': {'ID': 'other_flags', 'indx': 10},
                'solution_id': {'ID': 'solution_id', 'indx': 11}
                }
            )
    table = rseeker.get_table('_PKTable')
    for field in table.fields:
        field.ID = None
    assert (rseeker.get_id_index_mapping('_PKTable')
            == {'pksrcid': {'indx': 0, 'ID': 'pksrcid'},
                'pkband': {'indx': 1, 'ID': 'pkband'}
                }
            )
    for table in rseeker._resource.tables:
        table.ID = None
    assert rseeker.get_table_ids() == ['AnonymousTable', 'AnonymousTable']

    for table in rseeker._resource.tables:
        table.name = "any_name"

    assert rseeker.get_table_ids() == ['any_name', 'any_name']
    assert (rseeker.get_id_index_mapping('any_name')
            == {'pksrcid': {'indx': 0, 'ID': 'pksrcid'},
                'pkband': {'indx': 1, 'ID': 'pkband'}}
            )


@pytest.fixture
def data_path():
    return os.path.dirname(os.path.realpath(__file__))


if __name__ == '__main__':
    pytest.main()
