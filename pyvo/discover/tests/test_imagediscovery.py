# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.discover.image
"""

import weakref

import pytest

from astropy import coordinates
from astropy import time
from astropy import units as u

from pyvo import dal
from pyvo import discover
from pyvo import registry
from pyvo.discover import image
from pyvo.utils.testing import LearnableRequestMocker


class FakeQueriable:
    """a scaffolding class to record queries built by the various
    discovery methods.

    It's a stand-in for all of discover.Queriable, the resource record,
    and the services.  All query functions just make their search
    arguments available in search_args and search_kwargs attributes here
    and otherwise return whatever you pass in as return_this.
    """
    def __init__(self, return_this=[]):
        self.title = "Fake scaffold service"
        self.ivoid = "ivo://x-invalid/pyvo-fake"
        self.return_this = return_this
        self.res_rec = weakref.proxy(self)

    def get_service(self, service_type, **kwargs):
        return self

    def search(self, *args, **kwargs):
        self.search_args = args
        self.search_kwargs = kwargs
        return self.return_this

    run_sync = search


class FakeSIARec:
    """a convenience class to halfway easily create SIA1 records
    sufficient for testing.
    """
    defaults = {
        "bandpass_lolimit": 5e-7*u.m,
        "bandpass_hilimit": 7e-7*u.m,
        "dateobs": time.Time("1970-10-13T14:00:00"),
        "filesize": 20,
        "naxis": (10*u.pix, 20*u.pix),
        "naxes": 2,
        "pos": coordinates.SkyCoord(0*u.deg, 0*u.deg)}

    def __init__(self, **kwargs):
        for key, value in self.defaults.items():
            setattr(self, key, value)
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __getattr__(self, name):
        return None


class TestTimeCondition:
    def test_sia1(self):
        # this primarily tests for local filtering
        queriable = FakeQueriable([
            FakeSIARec(), FakeSIARec(dateobs=time.Time("1970-10-14"))])
        d = discover.ImageDiscoverer(
            space=(0, 0, 1),
            time=(
                time.Time("1970-10-13T13:00:00"),
                time.Time("1970-10-13T17:00:00")))
        d._query_one_sia1(queriable)
        assert len(d.results) == 1
        assert abs(d.results[0].t_min-40872.583333333336)<1e-10
        assert queriable.search_kwargs == {
            'pos': (0, 0), 'size': 1, 'intersect': 'overlaps'}

    def test_sia1_nointerval(self):
        queriable = FakeQueriable([
            FakeSIARec(), FakeSIARec(dateobs=time.Time("1970-10-14"))])
        d = discover.ImageDiscoverer(
            space=(0, 0, 1),
            time=time.Time("1970-10-13T13:00:02"))
        d._query_one_sia1(queriable)
        assert len(d.results) == 1

    def test_sia2(self):
        queriable = FakeQueriable()
        d = discover.ImageDiscoverer(
            time=(
                time.Time("1970-10-13T13:00:00"),
                time.Time("1970-10-13T17:00:00")))
        d._query_one_sia2(queriable)

        assert set(queriable.search_kwargs) == set(["time"])
        assert abs(queriable.search_kwargs["time"
            ][0].utc.value-40872.54166667)<1e-8

    def test_sia2_nointerval(self):
        queriable = FakeQueriable()
        d = discover.ImageDiscoverer(
            time=time.Time("1970-10-13T13:00:00"))
        d._query_one_sia2(queriable)

        assert set(queriable.search_kwargs) == set(["time"])
        assert abs(queriable.search_kwargs["time"
            ][0].utc.value-40872.54166667)<1e-8
        assert abs(queriable.search_kwargs["time"
            ][1].utc.value-40872.54166667)<1e-8

    def test_obscore(self):
        queriable = FakeQueriable()
        d = discover.ImageDiscoverer(
            time=(
                time.Time("1970-10-13T13:00:00"),
                time.Time("1970-10-13T17:00:00")))
        d.obscore_recs = [queriable]
        d._query_obscore()

        assert set(queriable.search_kwargs) == set()
        assert queriable.search_args[0] == (
            "select * from ivoa.obscore WHERE dataproduct_type='image' AND (t_max>=40872.541666666664 AND 40872.708333333336>=t_min AND t_min<=t_max AND 40872.541666666664<=40872.708333333336)")

    def test_obscore_nointerval(self):
        queriable = FakeQueriable()
        d = discover.ImageDiscoverer(
            time=(
                time.Time("1970-10-13T13:00:00")))
        d.obscore_recs = [queriable]
        d._query_obscore()

        assert set(queriable.search_kwargs) == set()
        assert queriable.search_args[0] == (
            "select * from ivoa.obscore WHERE dataproduct_type='image' AND (t_max>=40872.541666666664 AND 40872.541666666664>=t_min AND t_min<=t_max AND 40872.541666666664<=40872.541666666664)")


@pytest.fixture
def _sia1_responses(requests_mock):
    matcher = LearnableRequestMocker("sia1-responses")
    requests_mock.add_matcher(matcher)


def test_no_services_selected():
    with pytest.raises(dal.DALQueryError) as excinfo:
        image.ImageDiscoverer().query_services()
    assert "No services to query." in str(excinfo.value)


def test_single_sia1(_sia1_responses):
    results, log = discover.images_globally(
        space=(116, -29, 0.1),
        time=time.Time(56383.105520834, format="mjd"),
        services=registry.search(
            registry.Ivoid("ivo://org.gavo.dc/bgds/q/sia")))
    im = results[0]
    assert im.s_xel1 == 10800.
    assert isinstance(im.em_min, float)
    assert abs(im.s_dec+29)<2
    assert im.instrument_name == 'Robotic Bochum Twin Telescope (RoBoTT)'
    assert "BGDS GDS_" in im.obs_title
    assert "dc.zah.uni-heidelberg.de/getproduct/bgds/data" in im.access_url


@pytest.fixture
def _all_constraint_responses(requests_mock):
    matcher = LearnableRequestMocker("image-with-all-constraints")
    requests_mock.add_matcher(matcher)


def test_cone_and_spectral_point(_all_constraint_responses):
    images, logs = discover.images_globally(
        space=(134, 11, 0.1),
        spectrum=600*u.eV)

    assert ("Skipping ivo://org.gavo.dc/__system__/siap2/sitewide because"
        " it is served by ivo://org.gavo.dc/__system__/obscore/obscore"
        in logs)

    assert len(images) == 8
    assert images[0].obs_collection == "RASS"


@pytest.fixture
def _servedby_elision_responses(requests_mock):
    matcher = LearnableRequestMocker("servedby-elision-responses")
    requests_mock.add_matcher(matcher)


def test_servedby_elision(_servedby_elision_responses):
    d = discover.ImageDiscoverer(space=(3, 1, 0.2))
    # siap2/sitewide has isservedby to tap
    d.set_services(registry.search(registry.Ivoid(
       "ivo://org.gavo.dc/tap",
       "ivo://org.gavo.dc/__system__/siap2/sitewide")))

    assert d.sia2_recs == []
    assert len(d.obscore_recs) == 1
    assert d.obscore_recs[0].ivoid == "ivo://org.gavo.dc/tap"
    assert ('Skipping ivo://org.gavo.dc/__system__/siap2/sitewide because it is served by ivo://org.gavo.dc/tap'
        in d.log_messages)


@pytest.fixture
def _access_url_elision_responses(requests_mock):
    matcher = LearnableRequestMocker("access-url-elision")
    requests_mock.add_matcher(matcher)


def test_access_url_elision(_access_url_elision_responses):
    with pytest.warns():
        d = discover.ImageDiscoverer(
            time=time.Time("1910-07-15", scale="utc"),
            spectrum=400*u.nm)
    d.set_services(registry.search(registry.Ivoid(
       "ivo://org.gavo.dc/tap",
       "ivo://org.gavo.dc/__system__/siap2/sitewide")),
        # that's important here: we *want* to query the same stuff twice
       purge_redundant=False)
    d.query_services()

    # make sure we found anything at all
    assert d.results
    assert len([1 for l in d.log_messages if "skipped" in l]) == 0

    # make sure there are no duplicate records
    access_urls = [im.access_url for im in d.results]
    assert len(access_urls) == len(set(access_urls))
