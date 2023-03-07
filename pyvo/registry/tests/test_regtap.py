#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.registry.regtap
"""

import io
import re
from functools import partial
from urllib.parse import parse_qsl

import pytest

from pyvo.registry import regtap
from pyvo.registry import rtcons
from pyvo.registry.regtap import REGISTRY_BASEURL
from pyvo.registry import search as regsearch
from pyvo.dal import DALOverflowWarning
from pyvo.dal import query as dalq
from pyvo.dal import tap

from astropy.utils.data import get_pkg_data_contents

from .commonfixtures import messenger_vocabulary  # noqa: F401


get_pkg_data_contents = partial(
    get_pkg_data_contents, package=__package__, encoding='binary')


@pytest.fixture(name='capabilities')
def _capabilities(mocker):
    def callback(request, context):
        return get_pkg_data_contents('data/capabilities.xml')

    with mocker.register_uri(
        'GET', REGISTRY_BASEURL + '/capabilities', content=callback
    ) as matcher:
        yield matcher


# to update this, run
# import requests
# from pyvo.registry import regtap
#
# with open("data/regtap.xml", "wb") as f:
# 	f.write(requests.get(regtap.REGISTRY_BASEURL+"/sync", {
# 		"LANG": "ADQL",
# 		"QUERY": regtap.get_RegTAP_query(keywords="pulsar", ucd=["pos.distance"])}).content)


@pytest.fixture(name='regtap_pulsar_distance_response')
def _regtap_pulsar_distance_response(mocker):
    with mocker.register_uri(
        'POST', REGISTRY_BASEURL + '/sync',
            content=get_pkg_data_contents('data/regtap.xml')) as matcher:
        yield matcher


@pytest.fixture()
def keywords_fixture(mocker):
    def keywordstest_callback(request, context):
        data = dict(parse_qsl(request.body))
        query = data['QUERY']

        assert "res_subject ILIKE '%vizier%'" in query
        assert "ivo_hasword(res_description, 'vizier')" in query
        assert "1=ivo_hasword(res_title, 'vizier')" in query

        assert " res_subject ILIKE '%pulsar%'" in query
        assert "1=ivo_hasword(res_description, 'pulsar')" in query
        assert "1=ivo_hasword(res_title, 'pulsar')" in query

        return get_pkg_data_contents('data/regtap.xml')

    with mocker.register_uri(
        'POST', REGISTRY_BASEURL + '/sync',
        content=keywordstest_callback
    ) as matcher:
        yield matcher


@pytest.fixture()
def single_keyword_fixture(mocker):
    def keywordstest_callback(request, context):
        data = dict(parse_qsl(request.body))
        query = data['QUERY']

        assert "WHERE res_subject ILIKE '%single%'" in query
        assert "WHERE 1=ivo_hasword(res_description, 'single') UNION" in query
        assert "1=ivo_hasword(res_title, 'single')" in query

        return get_pkg_data_contents('data/regtap.xml')

    with mocker.register_uri(
        'POST', REGISTRY_BASEURL + '/sync',
        content=keywordstest_callback
    ) as matcher:
        yield matcher


@pytest.fixture()
def servicetype_fixture(mocker):
    def servicetypetest_callback(request, context):
        data = dict(parse_qsl(request.body))
        query = data['QUERY']

        assert "'ivo://ivoa.net/std/conesearch'" not in query
        assert "'ivo://ivoa.net/std/sia'" not in query
        assert "'ivo://ivoa.net/std/ssa'" not in query
        assert "'ivo://ivoa.net/std/slap'" not in query
        assert "'ivo://ivoa.net/std/tap'" in query

        return get_pkg_data_contents('data/regtap.xml')

    with mocker.register_uri(
        'POST', REGISTRY_BASEURL + '/sync',
        content=servicetypetest_callback
    ) as matcher:
        yield matcher


@pytest.fixture()
def waveband_fixture(mocker):
    def wavebandtest_callback(request, content):
        data = dict(parse_qsl(request.body))
        query = data['QUERY']

        assert "1 = ivo_hashlist_has(rr.resource.waveband, 'optical'" in query

        return get_pkg_data_contents('data/regtap.xml')

    with mocker.register_uri(
        'POST', REGISTRY_BASEURL + '/sync',
        content=wavebandtest_callback
    ) as matcher:
        yield matcher


@pytest.fixture()
def datamodel_fixture(mocker):
    def datamodeltest_callback(request, content):
        data = dict(parse_qsl(request.body))
        query = data['QUERY']

        assert (
            "(detail_xpath = '/capability/dataModel/@ivo-id'" in query)

        assert (
            "ivo_nocasematch(detail_value, 'ivo://ivoa.net/std/obscore%'))"
            in query)

        return get_pkg_data_contents('data/regtap.xml')

    with mocker.register_uri(
        'POST', REGISTRY_BASEURL + '/sync',
        content=datamodeltest_callback
    ) as matcher:
        yield matcher


@pytest.fixture()
def aux_fixture(mocker):
    def auxtest_callback(request, context):
        data = dict(parse_qsl(request.body))
        query = data['QUERY']

        assert "ivo://ivoa.net/std/tap#aux" in query

        return get_pkg_data_contents('data/regtap.xml')

    with mocker.register_uri(
        'POST', REGISTRY_BASEURL + '/sync',
        content=auxtest_callback,
    ) as matcher:
        yield matcher


@pytest.fixture(name='multi_interface_fixture')
def _multi_interface_fixture(mocker):
    # to update this, run
    # import requests
    # from pyvo.registry import regtap
    #
    # with open("data/multi-interface.xml", "wb") as f:
    # 	f.write(requests.get(regtap.REGISTRY_BASEURL+"/sync", {
    # 		"LANG": "ADQL",
    # 		"QUERY": regtap.get_RegTAP_query(
    # 			ivoid="ivo://org.gavo.dc/flashheros/q/ssa")}).content)
    with mocker.register_uri(
        'POST', REGISTRY_BASEURL + '/sync',
        content=get_pkg_data_contents('data/multi-interface.xml')
    ) as matcher:
        yield matcher


@pytest.fixture(name='flash_service')
def _flash_service(multi_interface_fixture):
    return regtap.search(
        ivoid="ivo://org.gavo.dc/flashheros/q/ssa")[0]


class TestInterfaceClass:
    def test_basic(self):
        intf = regtap.Interface("http://example.org", "", "", "")
        assert intf.access_url == "http://example.org"
        assert intf.standard_id is None
        assert intf.type is None
        assert intf.role is None
        assert intf.is_standard is False
        assert not intf.is_vosi

    def test_repr(self):
        intf = regtap.Interface("http://example.org", "ivo://gavo/std/a",
                                "vs:paramhttp", "std")
        assert (repr(intf) == "Interface('http://example.org',"
                " 'ivo://gavo/std/a', 'vs:paramhttp', 'std')")
        intf = regtap.Interface("http://example.org", "ivo://gavo/std/a",
                                None, None)
        assert repr(intf) == ("Interface('http://example.org',"
                              " 'ivo://gavo/std/a', None, None)")

    def test_unknown_standard(self):
        intf = regtap.Interface("http://example.org", "ivo://gavo/std/a",
                                "vs:paramhttp", "std")
        assert intf.is_standard
        with pytest.raises(ValueError) as excinfo:
            intf.to_service()

        assert str(excinfo.value) == (
            "PyVO has no support for interfaces with standard"
            " id ivo://gavo/std/a.")

    def test_known_standard(self):
        intf = regtap.Interface("http://example.org",
                                "ivo://ivoa.net/std/tap#aux", "vs:paramhttp", "std")
        assert isinstance(intf.to_service(), tap.TAPService)
        assert not intf.is_vosi

    def test_secondary_interface(self):
        intf = regtap.Interface("http://example.org",
                                "ivo://ivoa.net/std/tap#aux",
                                "vs:webbrowser", "web")

        with pytest.raises(ValueError) as excinfo:
            intf.to_service()

        assert str(excinfo.value) == (
            "This is not a standard interface.  PyVO cannot speak to it.")

    def test_VOSI(self):
        intf = regtap.Interface("http://example.org",
                                "ivo://ivoa.net/std/vosi#capabilities",
                                "vs:ParamHTTP", "std")
        assert intf.is_vosi


# The following tests have their assertions in the fixtures.
# It would certainly not hurt to refactor this so they are
# in the tests (we could also just rely on the rtcons tests
# that exercise about the same thing).

@pytest.mark.usefixtures('keywords_fixture', 'capabilities')
def test_keywords():
    regsearch(keywords=['vizier', 'pulsar'])


@pytest.mark.usefixtures('single_keyword_fixture', 'capabilities')
def test_single_keyword():
    regsearch(keywords=['single'])
    regsearch(keywords='single')


@pytest.mark.usefixtures('servicetype_fixture', 'capabilities')
def test_servicetype():
    regsearch(servicetype='table')


@pytest.mark.usefixtures(
    'waveband_fixture',
    'capabilities',
    'messenger_vocabulary')
def test_waveband():
    regsearch(waveband='optical')


@pytest.mark.usefixtures('datamodel_fixture', 'capabilities')
def test_datamodel():
    regsearch(datamodel='ObsCore')


@pytest.mark.usefixtures('aux_fixture', 'capabilities')
def test_servicetype_aux():
    regsearch(servicetype='table', includeaux=True)


@pytest.mark.usefixtures('aux_fixture', 'capabilities')
def test_bad_servicetype_aux():
    with pytest.raises(dalq.DALQueryError):
        regsearch(servicetype='bad_servicetype', includeaux=True)


class _NS:
    """a namespace exposing its keyword arguments as attributes.

    We need this here to let us conveniently construct _FakeResults.
    """
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class _FakeResults:
    """
    a minimal standin for dal.query.Results to be used with dal.query.Record.

    It is constructed with a dictionary that should eventually be
    used as the mapping in the Record.
    """
    def __init__(self, valdict):
        self.fieldnames = list(valdict.keys())
        self.resultstable = _NS(array=_NS(data=[list(valdict.values())]))


def get_regtap_results(**kwargs):
    """
    return a RegTAP result as expected by RegistryResult with all values
    empty, completed with what's in kwargs.
    """
    res = {}
    for key in regtap.RegistryResource.expected_columns:
        if isinstance(key, str):
            res[key] = None
        else:
            res[key[-1]] = None

    res.update(kwargs)
    return _FakeResults(res)


def test_spatial():
    assert (rtcons.keywords_to_constraints({
            "spatial": (23, -40)})[0].get_search_condition()
            == "1 = CONTAINS(MOC(6, POINT(23, -40)), coverage)")


def test_spectral():
    assert (rtcons.keywords_to_constraints({
            "spectral": (1e-17, 2e-17)})[0].get_search_condition()
            == "1 = ivo_interval_overlaps(spectral_start, spectral_end, 1e-17, 2e-17)")


def test_to_table(multi_interface_fixture, capabilities):
    t = regtap.search(
        ivoid="ivo://org.gavo.dc/flashheros/q/ssa").get_summary()
    assert (set(t.columns.keys())
            == {'index', 'short_name', 'title', 'description', 'interfaces'})
    assert t["index"][0] == 0
    assert t["title"][0] == 'Flash/Heros SSAP'
    assert (t["description"][0][:40]
            == 'Spectra from the Flash and Heros Echelle')
    assert (t["interfaces"][0]
            == 'datalink#links-1.0, soda#sync-1.0, ssa, tap#aux, web')


@pytest.fixture(name='rt_pulsar_distance')
def _rt_pulsar_distance(regtap_pulsar_distance_response, capabilities):
    return regsearch(keywords="pulsar", ucd=["pos.distance"])


def test_record_fields(rt_pulsar_distance):
    rec = rt_pulsar_distance["VII/156"]
    assert rec.ivoid == "ivo://cds.vizier/vii/156"
    assert rec.res_type == "vs:catalogservice"
    assert rec.short_name == "VII/156"
    assert rec.res_title == "Catalog of 558 Pulsars"
    assert rec.content_levels == ['research']
    assert rec.res_description[:20] == "The catalogue is an up-to-date"[:20]
    assert rec.reference_url == "http://cdsarc.unistra.fr/cgi-bin/cat/VII/156"
    assert rec.creators == ['Taylor J.H.', ' Manchester R.N.', ' Lyne A.G.']
    assert rec.content_types == ['catalog']
    assert rec.source_format == "bibcode"
    assert rec.source_value == "1993ApJS...88..529T"
    assert rec.waveband == ['radio']
    # access URL, standard_id and friends exercised in TestInterfaceSelection


class TestResultIndexing:
    def test_get_with_index(self, rt_pulsar_distance):
        # this is expecte to break when the fixture is updated
        assert (rt_pulsar_distance[0].res_title
                == 'Pulsar Timing for Fermi Gamma-ray Space Telescope')

    def test_get_with_short_name(self, rt_pulsar_distance):
        assert (rt_pulsar_distance["ATNF"].res_title
                == 'ATNF Pulsar Catalog')

    def test_get_with_ivoid(self, rt_pulsar_distance):
        assert (rt_pulsar_distance["ivo://nasa.heasarc/atnfpulsar"
                                   ].res_title == 'ATNF Pulsar Catalog')

    def test_out_of_range(self, rt_pulsar_distance):
        with pytest.raises(IndexError) as excinfo:
            rt_pulsar_distance[40320]
        assert (str(excinfo.value)
                == "index 40320 is out of bounds for axis 0 with size 23")

    def test_bad_key(self, rt_pulsar_distance):
        with pytest.raises(KeyError) as excinfo:
            rt_pulsar_distance["hunkatunka"]
        assert (str(excinfo.value) == "'hunkatunka'")

    def test_not_indexable(self, rt_pulsar_distance):
        with pytest.raises(IndexError) as excinfo:
            rt_pulsar_distance[None]
        assert (str(excinfo.value)
                == "No resource matching None")


@pytest.mark.usefixtures('multi_interface_fixture', 'capabilities',
                         'flash_service')
class TestInterfaceSelection:
    """
    tests for the selection and generation of services within
    RegistryResource.
    """

    def test_exactly_one_result(self):
        results = regtap.search(
            ivoid="ivo://org.gavo.dc/flashheros/q/ssa")
        assert len(results) == 1

    def test_access_modes(self, flash_service):
        assert set(flash_service.access_modes()) == {
            'datalink#links-1.0', 'soda#sync-1.0', 'ssa', 'tap#aux',
            'web'}

    def test_standard_id_multi(self, flash_service):
        with pytest.raises(dalq.DALQueryError) as excinfo:
            _ = flash_service.standard_id

        assert str(excinfo.value) == ("This resource supports several"
                                      " standards (datalink#links-1.0, soda#sync-1.0, ssa,"
                                      " tap#aux, web).  Use get_service or restrict your query"
                                      " using Servicetype.")

    def test_get_web_interface(self, flash_service):
        svc = flash_service.get_service("web")
        assert isinstance(svc,
                          regtap._BrowserService)
        assert (svc.access_url
                == "http://dc.zah.uni-heidelberg.de/flashheros/q/web/form")

    def test_get_aux_interface(self, flash_service):
        svc = flash_service.get_service("tap#aux")
        assert (svc._baseurl
                == "http://dc.zah.uni-heidelberg.de/tap")

    def test_get_aux_as_main(self, flash_service):
        assert (flash_service.get_service("tap")._baseurl
                == "http://dc.zah.uni-heidelberg.de/tap")

    def test_get__main_from_aux(self, flash_service):
        assert (flash_service.get_service("tap")._baseurl
                == "http://dc.zah.uni-heidelberg.de/tap")

    def test_get_by_alias(self, flash_service):
        assert (flash_service.get_service("spectrum")._baseurl
                == "http://dc.zah.uni-heidelberg.de/fhssa?")

    def test_get_unsupported_standard(self, flash_service):
        with pytest.raises(ValueError) as excinfo:
            flash_service.get_service("soda#sync-1.0")

        assert str(excinfo.value) == (
            "PyVO has no support for interfaces with standard id"
            " ivo://ivoa.net/std/soda#sync-1.0.")

    def test_get_nonexisting_standard(self, flash_service):
        with pytest.raises(ValueError) as excinfo:
            flash_service.get_service("http://nonsense#fancy")

        assert str(excinfo.value) == (
            "No matching interface.")

    def test_unconstrained(self, flash_service):
        with pytest.raises(ValueError) as excinfo:
            flash_service.get_service(lax=False)

        assert str(excinfo.value) == (
            "Multiple matching interfaces found.  Perhaps pass in"
            " service_type or use a Servicetype constrain in the"
            " registry.search?  Or use lax=True?")

    def test_interface_without_role(self):
        # There's an ugly corner case in our array simulation for
        # capabilities and interfaces: if there's a single untyped
        # interface, the returned type (or role) will be an empty
        # string, and the split() will return an empty list.
        # This swallowed the interface in pyVO 1.3.
        rec = get_regtap_results(
            access_urls="http://example.org/tap",
            standard_ids="ivo://ivoa.net/std/TAP",
            intf_types="vr:webbrowser",
            intf_roles="")

        resource = regtap.RegistryResource(rec, 0)
        assert len(resource.interfaces) == 1
        assert resource.interfaces[0].standard_id == 'ivo://ivoa.net/std/TAP'

        # get_service still won't work because it needs a paramhttp
        # interface (and a role="std").
        with pytest.raises(ValueError) as excinfo:
            resource.get_service('tap')
        assert (str(excinfo.value) == "No matching interface.")


class _FakeResult:
    """A fake class just sufficient for giving dal.query.Record enough
    to pull in the dict this is constructed.

    As an extra service, list values are stringified with
    regtap.TOKEN_SEP -- this is how they ought to come in from
    RegTAP services.
    """

    def __init__(self, d):
        self.fieldnames = list(d.keys())
        vals = [regtap.TOKEN_SEP.join(v) if isinstance(v, list) else v
                for v in d.values()]

        class _:
            class array:
                data = [vals]

        self.resultstable = _


def _makeRegistryRecord(overrides):
    """returns a minimal RegistryResource instance, overriding
    some built-in defaults with the dict overrides.
    """
    defaults = {
        "access_urls": "",
        "standard_ids": "",
        "intf_types": "",
        "intf_roles": "",
        "ivoid": "ivo://pyvo/test_regtap.py"
    }
    defaults.update(overrides)
    return regtap.RegistryResource(_FakeResult(defaults), 0)


class TestInterfaceRejection:
    """tests for various artificial corner cases where interface selection
    should fail (or just not fail).
    """

    def test_nonunique(self):
        rsc = _makeRegistryRecord({
            "access_urls": ["http://a", "http://b"],
            "standard_ids": ["ivo://ivoa.net/std/tap"] * 2,
            "intf_types": ["vs:paramhttp"] * 2,
            "intf_roles": ["std"] * 2,
        })
        with pytest.raises(ValueError) as excinfo:
            rsc.get_service("tap", lax=False)

        assert str(excinfo.value) == (
            "Multiple matching interfaces found.  Perhaps pass in"
            " service_type or use a Servicetype constrain in the"
            " registry.search?  Or use lax=True?")

    def test_nonunique_lax(self):
        rsc = _makeRegistryRecord({
            "access_urls": ["http://a", "http://b"],
            "standard_ids": ["ivo://ivoa.net/std/tap"] * 2,
            "intf_types": ["vs:paramhttp"] * 2,
            "intf_roles": ["std"] * 2,
        })

        assert (rsc.get_service("tap")._baseurl
                == "http://a")

    def test_nonstd_ignored(self):
        rsc = _makeRegistryRecord({
            "access_urls": ["http://a", "http://b"],
            "standard_ids": ["ivo://ivoa.net/std/tap"] * 2,
            "intf_types": ["vs:paramhttp"] * 2,
            "intf_roles": ["std", ""]
        })

        assert (rsc.get_service("tap", lax=False)._baseurl
                == "http://a")

    def test_select_single_matching_service(self):
        rsc = _makeRegistryRecord({
            "access_urls": ["http://a", "http://b"],
            "standard_ids": ["", "ivo://ivoa.net/std/tap"],
            "intf_types": ["vs:webbrowser", "vs:paramhttp"],
            "intf_roles": ["", "std"]
        })

        assert (rsc.service._baseurl == "http://b")

    def test_capless(self):
        rsc = _makeRegistryRecord({})

        with pytest.raises(ValueError) as excinfo:
            rsc.service._baseurl

        assert str(excinfo.value) == (
            "No matching interface.")


@pytest.mark.remote_data
def test_maxrec():
    with pytest.warns(DALOverflowWarning) as w:
        _ = regsearch(servicetype="tap", maxrec=1)
    assert len(w) == 1
    assert str(w[0].message).startswith("Partial result set.")


@pytest.mark.remote_data
def test_get_contact():
    rsc = _makeRegistryRecord(
        {"ivoid": "ivo://org.gavo.dc/flashheros/q/ssa"})
    assert (rsc.get_contact()
            == "GAVO Data Center Team (++49 6221 54 1837)"
            " <gavo@ari.uni-heidelberg.de>")


@pytest.mark.remote_data
class TestDatamodelQueries:
    # right now, the data model queries are all rather sui generis, and
    # rather fickly on top.  Let's make sure they actually return something
    # against the live registry.  Admittedly, this is about as much
    # a test of the VO infrastructure as of pyvo.

    def test_obscore(self):
        assert len(regsearch(rtcons.Datamodel('obscore'))) > 0

    def test_epntap(self):
        assert len(regsearch(rtcons.Datamodel('epntap'))) > 0

    def test_regtap(self):
        assert len(regsearch(rtcons.Datamodel('regtap'))) > 0


@pytest.mark.usefixtures('multi_interface_fixture', 'capabilities',
                         'flash_service')
class TestExtraResourceMethods:
    """
    tests for methods of RegistryResource containing some non-trivial
    logic (except service selection, which is in TestInterfaceSelection,
    and get_tables, which is in TestGetTables).
    """

    def test_unique_standard_id(self):
        rsc = _makeRegistryRecord({
            "access_urls": ["http://a"],
            "standard_ids": ["ivo://ivoa.net/std/tap"],
            "intf_types": ["vs:paramhttp"],
            "intf_roles": ["std"]
        })
        assert rsc.standard_id == "ivo://ivoa.net/std/tap"

    def test_describe_multi(self, flash_service):
        out = io.StringIO()
        flash_service.describe(verbose=True, file=out)
        output = out.getvalue()

        assert "Flash/Heros SSAP" in output
        assert ("Access modes: datalink#links-1.0, soda#sync-1.0,"
                " ssa, tap#aux, web" in output)
        assert "Multi-capabilty service" in output

        assert "More info: http://dc.zah" in output

    def test_no_access_url(self):
        rsc = _makeRegistryRecord({
            "access_urls": [],
            "standard_ids": [],
            "intf_types": [],
            "intf_roles": []
        })
        with pytest.raises(dalq.DALQueryError) as excinfo:
            rsc.access_url

        assert str(excinfo.value) == ("The resource"
                                      " ivo://pyvo/test_regtap.py has no queriable interfaces.")

    def test_unique_access_url(self):
        rsc = _makeRegistryRecord({
            "access_urls": ["http://a"],
            "standard_ids": ["ivo://ivoa.net/std/tap"],
            "intf_types": ["vs:paramhttp"],
            "intf_roles": [""]
        })
        assert rsc.access_url == "http://a"

    def test_ambiguous_access_url_warns(self, recwarn):
        rsc = _makeRegistryRecord({
            "access_urls": ["http://a", "http://b"],
            "standard_ids": ["ivo://ivoa.net/std/tap"] * 2,
            "intf_types": ["vs:paramhttp"] * 2,
            "intf_roles": ["std"] * 2,
        })
        assert rsc.access_url == "http://a"
        assert ('The resource ivo://pyvo/test_regtap.py has multipl' in
                [str(w.message)[:50] for w in recwarn])


# TODO: While I suppose the contact test should keep requiring network,
# I think we should can the network responses involved in the following;
# the stuff might change upstream any time and then break our unit tests.
@pytest.mark.remote_data
@pytest.fixture(name='flash_tables')
def _flash_tables():
    rsc = _makeRegistryRecord(
        {"ivoid": "ivo://org.gavo.dc/flashheros/q/ssa"})
    return rsc.get_tables()


@pytest.mark.usefixtures("flash_tables")
class TestGetTables:
    @pytest.mark.remote_data
    def test_get_tables_limit_enforced(self):
        rsc = _makeRegistryRecord(
            {"ivoid": "ivo://org.gavo.dc/tap"})
        with pytest.raises(dalq.DALQueryError) as excinfo:
            rsc.get_tables()

        assert re.match(r"Resource ivo://org.gavo.dc/tap reports \d+ tables."
                        "  Pass a higher table_limit to see them all.", str(excinfo.value))

    @pytest.mark.remote_data
    def test_get_tables_names(self, flash_tables):
        assert (list(sorted(flash_tables.keys()))
                == ["flashheros.data", "ivoa.obscore"])

    @pytest.mark.remote_data
    def test_get_tables_table_instance(self, flash_tables):
        assert (flash_tables["ivoa.obscore"].name
                == "ivoa.obscore")
        assert (flash_tables["ivoa.obscore"].description
                == "This data collection is queryable in GAVO Data"
                " Center's obscore table.")
        assert (flash_tables["flashheros.data"].title
                == "Flash/Heros SSA table")

        assert (flash_tables["flashheros.data"].origin.ivoid
                == "ivo://org.gavo.dc/flashheros/q/ssa")

    @pytest.mark.remote_data
    def test_get_tables_column_meta(self, flash_tables):
        def getflashcol(name):
            for col in flash_tables["flashheros.data"].columns:
                if name == col.name:
                    return col
            raise KeyError(name)

        assert getflashcol("accref").datatype.content == "char"
        assert getflashcol("accref").datatype.arraysize == "*"

# TODO: upstream bug: the following needs to fixed in DaCHS before
# the assertion passes
        # assert getflashcol("ssa_region").datatype._extendedtype == "point"

        assert getflashcol("mime").ucd == 'meta.code.mime'

        assert getflashcol("ssa_specend").unit == "m"

        assert (getflashcol("ssa_specend").utype
                == "ssa:char.spectralaxis.coverage.bounds.stop")

        assert (getflashcol("ssa_fluxcalib").description
                == "Type of flux calibration")
