#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.registry.rtcons, i.e. RegTAP constraints and query building.
"""

import datetime

import numpy
import pytest

from pyvo.registry import rtcons
from pyvo.dal import query as dalq


class TestAbstractConstraint:
    def test_no_search_condition(self):
        with pytest.raises(NotImplementedError):
            rtcons.Constraint().get_search_condition()


class TestSQLLiterals:
    @pytest.fixture(scope="class", autouse=True)
    def literals(self):
        class _WithFillers(rtcons.Constraint):
            _fillers = {
                "aString": "some harmless stuff",
                "nastyString": "that's not nasty",
                "bytes": b"keep this ascii for now",
                "anInt": 210,
                "aFloat": 5e7,
                "numpyStuff": numpy.float96(23.7),
                "timestamp": datetime.datetime(2021, 6, 30, 9, 1),}

        return _WithFillers()._get_sql_literals()

   
    def test_strings(self, literals):
        assert literals["aString"] == "'some harmless stuff'"
        assert literals["nastyString"] == "'that''s not nasty'"

    def test_bytes(self, literals):
        assert literals["bytes"] == "'keep this ascii for now'"

    def test_int(self, literals):
        assert literals["anInt"] == "210"

    def test_float(self, literals):
        assert literals["aFloat"] == "50000000.0"

    def test_numpy(self, literals):
        assert literals["numpyStuff"][:14] == "23.69999999999"

    def test_timestamp(self, literals):
        assert literals["timestamp"] == "'2021-06-30T09:01:00'"

    def test_odd_type_rejected(self):
        with pytest.raises(ValueError) as excinfo:
            rtcons.make_sql_literal({})
        assert str(excinfo.value) == "Cannot format {} as a SQL literal"


class TestFreetextConstraint:
    def test_basic(self):
        assert (rtcons.Freetext("star").get_search_condition()
            == "ivoid IN (SELECT ivoid FROM rr.resource WHERE 1=ivo_hasword(res_description, 'star') UNION SELECT ivoid FROM rr.resource WHERE 1=ivo_hasword(res_title, 'star') UNION SELECT ivoid FROM rr.res_subject WHERE res_subject ILIKE '%star%')")

    def test_interesting_literal(self):
        assert (rtcons.Freetext("α Cen's planets").get_search_condition()
            == "ivoid IN (SELECT ivoid FROM rr.resource WHERE 1=ivo_hasword(res_description, 'α Cen''s planets') UNION SELECT ivoid FROM rr.resource WHERE 1=ivo_hasword(res_title, 'α Cen''s planets') UNION SELECT ivoid FROM rr.res_subject WHERE res_subject ILIKE '%α Cen''s planets%')")


class TestAuthorConstraint:
    def test_basic(self):
        assert (rtcons.Author("%Hubble%").get_search_condition()
            == "role_name LIKE '%Hubble%' AND base_role='creator'")


class TestServicetypeConstraint:
    def test_standardmap(self):
        assert (rtcons.Servicetype("scs").get_search_condition()
            == "standard_id IN ('ivo://ivoa.net/std/conesearch')")
    
    def test_fulluri(self):
        assert (rtcons.Servicetype("http://extstandards/invention"
                ).get_search_condition()
            == "standard_id IN ('http://extstandards/invention')")

    def test_multi(self):
        assert (rtcons.Servicetype("http://extstandards/invention", "image"
                ).get_search_condition()
            == "standard_id IN ('http://extstandards/invention',"
                " 'ivo://ivoa.net/std/sia')")

    def test_includeaux(self):
        assert (rtcons.Servicetype("http://extstandards/invention", "image"
                ).include_auxiliary_services().get_search_condition()
            == "standard_id IN ('http://extstandards/invention',"
                " 'http://extstandards/invention#aux',"
                " 'ivo://ivoa.net/std/sia',"
                " 'ivo://ivoa.net/std/sia#aux')")

    def test_junk_rejected(self):
        with pytest.raises(dalq.DALQueryError) as excinfo:
            rtcons.Servicetype("junk")
        assert str(excinfo.value) == ("Service type junk is neither"
            " a full standard URI nor one of the bespoke identifiers"
            " image, spectrum, scs, line, table")


# TODO: add a vocabulary check and mark this as requiring networking
class TestWavebandConstraint:
    def test_basic(self):
        assert (rtcons.Waveband("Infrared", "EUV").get_search_condition()
            == "1 = ivo_hashlist_has(rr.resource.waveband, 'Infrared')"
                " OR 1 = ivo_hashlist_has(rr.resource.waveband, 'EUV')")


class TestDatamodelConstraint:
    def test_junk_rejected(self):
        with pytest.raises(dalq.DALQueryError) as excinfo:
            rtcons.Datamodel("junk")
        assert str(excinfo.value) == (
            "Unknown data model id junk.  Known are: epntap, obscore, regtap.")
    
    def test_obscore(self):
        cons = rtcons.Datamodel("ObsCore")
        assert (cons.get_search_condition()
            == "detail_xpath = '/capability/dataModel/@ivo-id'"
            " AND 1 = ivo_nocasematch(detail_value,"
                " 'ivo://ivoa.net/std/obscore%')")
        assert(cons._extra_tables==["rr.res_detail"])

    def test_epntap(self):
        cons = rtcons.Datamodel("epntap")
        assert (cons.get_search_condition()
            == "table_utype LIKE ivo://vopdc.obspm/std/epncore#schema-2.%'"
            " OR table_utype LIKE ivo://ivoa.net/std/epntap#table-2.%'")
        assert(cons._extra_tables==["rr.res_table"])

    def test_regtap(self):
        cons = rtcons.Datamodel("regtap")
        assert (cons.get_search_condition()
            == "detail_xpath = '/capability/dataModel/@ivo-id'"
            " AND 1 = ivo_nocasematch(detail_value,"
                " 'ivo://ivoa.net/std/RegTAP#1.%')")
        assert(cons._extra_tables==["rr.res_detail"])




class TestWhereClauseBuilding:
    @staticmethod
    def where_clause_for(*args, **kwargs):
        cons = list(args)+rtcons.keywords_to_constraints(kwargs)
        return rtcons.build_regtap_query(cons
            ).split("\nWHERE\n", 1)[1].split("\nGROUP BY\n")[0]

    def test_from_constraints(self):
        assert self.where_clause_for(
            rtcons.Waveband("EUV"),
            rtcons.Author("%Hubble%")
            ) == ("(1 = ivo_hashlist_has(rr.resource.waveband, 'EUV'))\n"
                "  AND (role_name LIKE '%Hubble%' AND base_role='creator')")

    def test_from_keywords(self):
        assert self.where_clause_for(
            waveband="EUV",
            author="%Hubble%"
            ) == ("(1 = ivo_hashlist_has(rr.resource.waveband, 'EUV'))\n"
                "  AND (role_name LIKE '%Hubble%' AND base_role='creator')")


    def test_mixed(self):
        assert self.where_clause_for(
            rtcons.Waveband("EUV"),
            author="%Hubble%"
            ) == ("(1 = ivo_hashlist_has(rr.resource.waveband, 'EUV'))\n"
                "  AND (role_name LIKE '%Hubble%' AND base_role='creator')")


    def test_bad_keyword(self):
        with pytest.raises(TypeError) as excinfo:
            rtcons.build_regtap_query(
                *rtcons.keywords_to_constraints({"foo": "bar"}))
        # the following assertion will fail when new constraints are
        # defined (or old ones vanish).  I'd say that's a convenient
        # way to track changes; so, let's update the assertion as we
        # go.
        assert str(excinfo.value) == ("foo is not a valid registry"
            " constraint keyword.  Use one of"
            " author, datamodel, keywords, servicetype, waveband.")


class TestSelectClause:
    def test_expected_columns(self):
        # This will break as regtap.RegistryResource.expected_columns
        # is changed.  Just update the assertion then.
        assert rtcons.build_regtap_query(
            rtcons.keywords_to_constraints({"author": "%Hubble%"})
            ).split("\nFROM rr.resource\n")[0] == (
            "SELECT\n"
            "ivoid, "
            "res_type, "
            "short_name, "
            "title, "
            "content_level, "
            "res_description, "
            "reference_url, "
            "creator_seq, "
            "content_type, "
            "source_format, "
            "region_of_regard, "
            "waveband, "
            "ivo_string_agg(access_url, ':::py VO sep:::') AS access_urls, "
            "ivo_string_agg(standard_id, ':::py VO sep:::') AS standard_ids, "
            "ivo_string_agg(intf_role, ':::py VO sep:::') AS intf_roles")

    def test_group_by_columns(self):
        # Again, this will break as regtap.RegistryResource.expected_columns
        # is changed.  Just update the assertion then.
        assert rtcons.build_regtap_query([rtcons.Author("%Hubble%")]
            ).split("\nGROUP BY\n")[-1] == (
            "ivoid, "
            "res_type, "
            "short_name, "
            "title, "
            "content_level, "
            "res_description, "
            "reference_url, "
            "creator_seq, "
            "content_type, "
            "source_format, "
            "region_of_regard, "
            "waveband")

