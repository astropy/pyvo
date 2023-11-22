# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Test for mivot.seekers.resource_seeker.py
"""
import os
import pytest
from astropy.io.votable import parse
from pyvo.mivot.seekers.resource_seeker import ResourceSeeker
from pyvo.mivot.version_checker import check_astropy_version
from pyvo.utils import activate_features
activate_features('MIVOT')


@pytest.fixture
def rseeker(data_path):
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")
    # Parse the VOTable and returns a ResourceSeeker based on the resources
    vpath = os.path.join(data_path, "data/input/test_ressource_seeker.xml")
    votable = parse(vpath)
    rseeker = None
    for resource in votable.resources:
        rseeker = ResourceSeeker(resource)
        break
    return rseeker


def test_id_table(rseeker, data_path):
    """
    Checks the IDs of tables found by the RessourceSeeker,
    checks the IDs of the field of the table concerned.
    """
    if check_astropy_version() is False:
        pytest.skip("MIVOT test skipped because of the astropy version.")

    assert rseeker.get_table_ids() == ['_PKTable', 'Results']

    assert rseeker.get_id_index_mapping('_PKTable') == {'_pksrcid': 0, '_pkband': 1}
    assert (rseeker.get_id_index_mapping('Results')
            == {'_srcid': 0, 'transit_id': 1, '_band': 2, '_obstime': 3, '_mag': 4,
                '_flux': 5, '_fluxerr': 6, 'flux_over_error': 7, 'rejected_by_photometry': 8,
                'rejected_by_variability': 9, 'other_flags': 10, 'solution_id': 11})
    table = rseeker.get_table('_PKTable')

    for field in table.fields:
        field.ID = None
    assert rseeker.get_id_index_mapping('_PKTable') == {'pksrcid': 0, 'pkband': 1}

    for table in rseeker._resource.tables:
        table.ID = None

    assert rseeker.get_table_ids() == ['AnonymousTable', 'AnonymousTable']
    for table in rseeker._resource.tables:
        table.name = "any_name"
    assert rseeker.get_table_ids() == ['any_name', 'any_name']
    assert rseeker.get_id_index_mapping('any_name') == {'pksrcid': 0, 'pkband': 1}


@pytest.fixture
def data_path():
    return os.path.dirname(os.path.realpath(__file__))


if __name__ == '__main__':
    pytest.main()
