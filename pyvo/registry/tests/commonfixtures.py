# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Common fixtures for pyVO registry tests
"""

import pytest

from astropy.utils.data import (
    clear_download_cache,
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


# The moc UAT was produced by this program:
# import json
# import pyvo
#
# def gather_children(voc, t):
# 	result = {t}
# 	voc[t].pop("description", None)
# 	for c in voc[t]["narrower"]:
# 		result |= gather_children(voc, c)
# 	return result
#
# uat = pyvo.utils.vocabularies.get_vocabulary("uat")
# solphys = gather_children(uat["terms"], "solar-physics")
# uat["terms"] = {t: m for t, m in uat["terms"].items()
# 	if t in solphys}
# with open("uat-selection.desise", "w", encoding="utf-8") as f:
# 	json.dump(uat, f, indent=1)

@pytest.fixture()
def uat_vocabulary(mocker):
    """a small sample of the IVOA UAT vocabulary in astropy's cache.

    We need to clean up behind ourselves, because our version of the
    UAT is limited to the solar-physics branch in order to not waste
    too much space.  The source code here contains a program to refresh
    this vocabulary selection.
    """
    import_file_to_cache(
        'http://www.ivoa.net/rdf/uat',
        get_pkg_data_filename(
            'data/uat-selection.desise',
            package=__package__))
    yield
    # it would be nice if we only did that if we polluted the
    # cache before the yield, but we can't easily see if we did that.
    clear_download_cache('http://www.ivoa.net/rdf/uat')


# We need an object standing in for TAP services for query generation.
# It would perhaps be nice to pull up a real TAPService instance from
# capabilities and tables, but that's a non-trivial amount of XML.
# Let's see how far we get with faking it.


class _FakeLanguage:
    """
    a stand-in for vosi.tapregext.Language for rtcons.Constrants.
    """
    def __init__(self, features):
        self.features = features

    def get_feature(self, type, form):
        return (type, form) in self.features


class _FakeTAPService:
    """
    A stand-in for a TAP service intended for rtcons.Constraints.

    features is a set of (type, form) tuples for now.
    tables is a dict with table names as keys (let's worry about the values
    later).
    """
    def __init__(self, features, tables):
        self.tables = tables
        adql_lang = _FakeLanguage(features)

        class _:
            def get_adql(otherself):
                return adql_lang
        self.tap_cap = _()

    def get_tap_capability(self):
        return self.tap_cap


FAKE_GAVO = _FakeTAPService({
    ("ivo://ivoa.net/std/TAPRegExt#features-adql-sets", "UNION"),
    ("ivo://org.gavo.dc/std/exts#extra-adql-keywords", "MOC"), }, {
        "rr.stc_spatial": None,
        "rr.stc_spectral": None,
        "rr.stc_temporal": None, })
FAKE_PLAIN = _FakeTAPService(frozenset(), {})
