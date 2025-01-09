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
from pyvo import registry
from pyvo.discover import image
from pyvo import discover


class TestImageFound:
    def testBadAttrName(self):
        with pytest.raises(TypeError):
            image.ImageFound("ivo://x-fake", {"invented": None})


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
        assert abs(d.results[0].t_min-40872.583333333336) < 1e-10
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
        assert abs(queriable.search_kwargs["time"][0].utc.value
            - 40872.54166667) < 1e-8

    def test_sia2_nointerval(self):
        queriable = FakeQueriable()
        d = discover.ImageDiscoverer(
            time=time.Time("1970-10-13T13:00:00"))
        d._query_one_sia2(queriable)

        assert set(queriable.search_kwargs) == set(["time"])
        assert abs(queriable.search_kwargs["time"][0].utc.value
            - 40872.54166667) < 1e-8
        assert abs(queriable.search_kwargs["time"][1].utc.value
            - 40872.54166667) < 1e-8

    def test_obscore(self):
        queriable = FakeQueriable()
        d = discover.ImageDiscoverer(
            time=(time.Time("1970-10-13T13:00:00"), time.Time("1970-10-13T17:00:00")))
        d.obscore_recs = [queriable]
        d._query_obscore()

        assert set(queriable.search_kwargs) == set()
        assert queriable.search_args[0] == (
            "select * from ivoa.obscore WHERE dataproduct_type='image'"
            " AND (t_max>=40872.541666666664 AND 40872.708333333336>=t_min"
            " AND t_min<=t_max AND 40872.541666666664<=40872.708333333336)")

    def test_obscore_nointerval(self):
        queriable = FakeQueriable()
        d = discover.ImageDiscoverer(
            time=(
                time.Time("1970-10-13T13:00:00")))
        d.obscore_recs = [queriable]
        d._query_obscore()

        assert set(queriable.search_kwargs) == set()
        assert queriable.search_args[0] == (
            "select * from ivoa.obscore WHERE dataproduct_type='image'"
            " AND (t_max>=40872.541666666664 AND 40872.541666666664>=t_min"
            " AND t_min<=t_max AND 40872.541666666664<=40872.541666666664)")


class TestSpaceCondition:
    def test_sia1_fails_without_space(self):
        queriable = FakeQueriable()
        di = discover.ImageDiscoverer(
            time=(
                time.Time("1970-10-13T13:00:00")))
        di.sia1_recs = [queriable]
        di.query_services()
        assert di.log_messages == [
            'SIA1 service(s) skipped due to missing space constraint']

    def test_sia2(self):
        queriable = FakeQueriable()
        di = discover.ImageDiscoverer(space=(30, 21, 1))
        di.sia2_recs = [queriable]
        di.query_services()
        assert queriable.search_kwargs == {'pos': (30, 21, 1)}

    def test_obscore(self):
        queriable = FakeQueriable()
        di = discover.ImageDiscoverer(space=(30, 21, 1))
        di.obscore_recs = [queriable]
        di.query_services()
        assert queriable.search_args == (
            "select * from ivoa.obscore WHERE dataproduct_type='image'"
            " AND (1=contains(point('ICRS', s_ra, s_dec),"
            " circle('ICRS', 30, 21, 1))"
            " or 1=intersects(circle(30, 21, 1), s_region))",)


def test_no_services_selected():
    with pytest.raises(dal.DALQueryError) as excinfo:
        image.ImageDiscoverer().query_services()
    assert "No services to query." in str(excinfo.value)


# Tests requiring remote data below this line


@pytest.mark.remote_data
def test_single_sia1():
    results, log = discover.images_globally(
        space=(116, -29, 0.1),
        time=time.Time(56383.105520834, format="mjd"),
        services=registry.search(
            registry.Ivoid("ivo://org.gavo.dc/bgds/q/sia")))
    im = results[0]
    assert im.s_xel1 == 10800.
    assert isinstance(im.em_min, float)
    assert abs(im.s_dec+29) < 2
    assert im.instrument_name == 'Robotic Bochum Twin Telescope (RoBoTT)'
    assert "BGDS GDS_" in im.obs_title
    assert "dc.g-vo.org/getproduct/bgds/data" in im.access_url


@pytest.mark.remote_data
def test_cone_and_spectral_point():
    # This should really return just a few services.  If this
    # starts hitting more services, see how we can throw them out
    # again, perhaps using a time constraint.
    watcher_msgs = []

    def test_watcher(disco, msg):
        watcher_msgs.append(msg)

    images, logs = discover.images_globally(
        space=(134, 11, 0.1),
        spectrum=600*u.eV,
        time=(time.Time('1990-01-01'), time.Time('1999-12-31')),
        watcher=test_watcher)

    assert len(logs) < 10, ("Too many services in test_cone_and_spectral."
        "  Try constraining the discovery phase more tightly to"
        " keep this test economical")

    skip_msg = ("Skipping ivo://org.gavo.dc/__system__/siap2/sitewide because"
        " it is served by ivo://org.gavo.dc/__system__/obscore/obscore")
    assert skip_msg in logs
    assert skip_msg in watcher_msgs

    assert len(images) >= 8
    assert "RASS" in {im.obs_collection for im in images}


@pytest.mark.remote_data
def test_servedby_elision():
    d = discover.ImageDiscoverer(space=(3, 1, 0.2))
    # siap2/sitewide has isservedby to tap
    d.set_services(
        registry.search(
            registry.Ivoid(
                "ivo://org.gavo.dc/tap",
                "ivo://org.gavo.dc/__system__/siap2/sitewide")))

    assert d.sia2_recs == []
    assert len(d.obscore_recs) == 1
    assert repr(d.obscore_recs[0]) == "<ivo://org.gavo.dc/tap>"
    assert ('Skipping ivo://org.gavo.dc/__system__/siap2/sitewide'
        ' because it is served by ivo://org.gavo.dc/tap' in d.log_messages)


@pytest.mark.remote_data
def test_access_url_elision():
    with pytest.warns():
        di = discover.ImageDiscoverer(
            time=time.Time("1910-07-15", scale="utc"),
            spectrum=400*u.nm)
    di.set_services(
        registry.search(
            registry.Ivoid(
                "ivo://org.gavo.dc/tap",
                "ivo://org.gavo.dc/__system__/siap2/sitewide")),
        # that's important here: we *want* to query the same stuff twice
       purge_redundant=False)
    di.query_services()

    # make sure we found anything at all
    assert di.results
    assert len([1 for lm in di.log_messages if "skipped" in lm]) == 0

    # make sure there are no duplicate records
    access_urls = [im.access_url for im in di.results]
    assert len(access_urls) == len(set(access_urls))


@pytest.mark.remote_data
def test_cancelling():

    def query_killer(disco, msg):
        if msg.startswith("Querying") and di.already_queried > 0:
            disco.reset_services()

    di = discover.ImageDiscoverer(
        time=time.Time("1980-07-15", scale="utc"),
        spectrum=400*u.nm,
        timeout=1,
        watcher=query_killer)

    di.set_services(registry.search(servicetype="sia2"))
    di.query_services()

    assert ('Cancelling queries with 1 service(s) queried'
        in di.log_messages)
