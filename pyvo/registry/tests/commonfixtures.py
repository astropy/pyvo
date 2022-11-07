# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Common fixtures for pyVO registry tests
"""

import pytest

from astropy.utils.data import (
    get_pkg_data_filename,
    import_file_to_cache)
# We need to populate the vocabulary cache with our test data;
# we cannot use requests_mock here because a.u.data uses urllib.
from astropy.utils.data import _get_download_cache_loc, _url_to_dirname  # noqa: F401


@pytest.fixture()
def messenger_vocabulary(mocker):
    """the IVOA messenger vocabulary in astropy's cache.

    Should we clean up after ourselves?
    """
    import_file_to_cache(
        'http://www.ivoa.net/rdf/messenger',
        get_pkg_data_filename(
            'data/messenger.desise',
            package=__package__))


# We need an object standing in for TAP services for query generation.
# It would perhaps be nice to pull up a real TAPService instance from
# capabilities and tables, but that's a non-trivial amount of XML.
# Let's see how far we get with faking it.


class _FakeTAPService:
    def __init__(self):
        pass


FAKE_GAVO = _FakeTAPService()
