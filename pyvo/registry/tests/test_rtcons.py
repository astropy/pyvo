#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.registry.rtcons, i.e. RegTAP constraints and query building.
"""

import datetime

from astropy.time import Time
from astropy import units as u
from astropy.coordinates import SkyCoord
import numpy
import pytest

from pyvo import registry
from pyvo.registry import rtcons
from pyvo.dal import query as dalq

from .commonfixtures import messenger_vocabulary  # noqa: F401


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
                "numpyStuff": numpy.float64(23.7),
                "timestamp": datetime.datetime(2021, 6, 30, 9, 1), }

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
        assert float(literals["numpyStuff"]) - 23.7 < 1e-10

    def test_timestamp(self, literals):
        assert literals["timestamp"] == "'2021-06-30T09:01:00'"

    def test_odd_type_rejected(self):
        with pytest.raises(ValueError) as excinfo:
            rtcons.make_sql_literal({})
        assert str(excinfo.value) == "Cannot format {} as a SQL literal"


class TestFreetextConstraint:
    def test_basic(self):
        assert rtcons.Freetext("star").get_search_condition() == (
            "ivoid IN (SELECT ivoid FROM rr.resource WHERE 1=ivo_hasword(res_description, 'star') "
            "UNION SELECT ivoid FROM rr.resource WHERE 1=ivo_hasword(res_title, 'star') "
            "UNION SELECT ivoid FROM rr.res_subject WHERE res_subject ILIKE '%star%')")

    def test_interesting_literal(self):
        assert rtcons.Freetext("α Cen's planets").get_search_condition() == (
            "ivoid IN (SELECT ivoid FROM rr.resource WHERE 1=ivo_hasword(res_description, 'α Cen''s planets')"
            " UNION SELECT ivoid FROM rr.resource WHERE 1=ivo_hasword(res_title, 'α Cen''s planets')"
            " UNION SELECT ivoid FROM rr.res_subject WHERE res_subject ILIKE '%α Cen''s planets%')")


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
                                      " image, sia, spectrum, ssap, ssa, scs, conesearch, line, slap,"
                                      " table, tap")

    def test_legacy_term(self):
        assert (rtcons.Servicetype("conesearch").get_search_condition()
                == "standard_id IN ('ivo://ivoa.net/std/conesearch')")


@pytest.mark.usefixtures('messenger_vocabulary')
class TestWavebandConstraint:
    def test_basic(self):
        assert (rtcons.Waveband("Infrared", "EUV").get_search_condition()
                == "1 = ivo_hashlist_has(rr.resource.waveband, 'infrared')"
                " OR 1 = ivo_hashlist_has(rr.resource.waveband, 'euv')")

    def test_junk_rejected(self):
        with pytest.raises(dalq.DALQueryError) as excinfo:
            rtcons.Waveband("junk")
        assert str(excinfo.value) == (
            "Waveband junk is not in the IVOA messenger vocabulary http://www.ivoa.net/rdf/messenger.")

    def test_normalisation(self):
        assert (rtcons.Waveband("oPtIcAl").get_search_condition()
                == "1 = ivo_hashlist_has(rr.resource.waveband, 'optical')")


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
        assert (cons._extra_tables == ["rr.res_detail"])

    def test_epntap(self):
        cons = rtcons.Datamodel("epntap")
        assert (cons.get_search_condition()
                == "table_utype LIKE 'ivo://vopdc.obspm/std/epncore#schema-2.%'"
                " OR table_utype LIKE 'ivo://ivoa.net/std/epntap#table-2.%'")
        assert (cons._extra_tables == ["rr.res_table"])

    def test_regtap(self):
        cons = rtcons.Datamodel("regtap")
        assert (cons.get_search_condition()
                == "detail_xpath = '/capability/dataModel/@ivo-id'"
                " AND 1 = ivo_nocasematch(detail_value,"
                " 'ivo://ivoa.net/std/RegTAP#1.%')")
        assert (cons._extra_tables == ["rr.res_detail"])


class TestIvoidConstraint:
    def test_basic(self):
        cons = rtcons.Ivoid("ivo://example/some_path")
        assert (cons.get_search_condition()
                == "ivoid = 'ivo://example/some_path'")


class TestUCDConstraint:
    def test_basic(self):
        cons = rtcons.UCD("phot.mag;em.opt.%", "phot.mag;em.ir.%")
        assert (cons.get_search_condition()
                == "ucd LIKE 'phot.mag;em.opt.%' OR ucd LIKE 'phot.mag;em.ir.%'")


class TestSpatialConstraint:
    def test_point(self):
        cons = registry.Spatial([23, -40])
        assert cons.get_search_condition() == "1 = CONTAINS(MOC(6, POINT(23, -40)), coverage)"
        assert cons._extra_tables == ["rr.stc_spatial"]

    def test_circle_and_order(self):
        cons = registry.Spatial([23, -40, 0.25], order=7)
        assert cons.get_search_condition() == "1 = CONTAINS(MOC(7, CIRCLE(23, -40, 0.25)), coverage)"

    def test_polygon(self):
        cons = registry.Spatial([23, -40, 26, -39, 25, -43])
        assert cons.get_search_condition() == (
            "1 = CONTAINS(MOC(6, POLYGON(23, -40, 26, -39, 25, -43)), coverage)")

    def test_moc(self):
        cons = registry.Spatial("0/1-3 3/")
        assert cons.get_search_condition() == "1 = CONTAINS(MOC('0/1-3 3/'), coverage)"

    def test_SkyCoord(self):
        cons = registry.Spatial(SkyCoord(3 * u.deg, -30 * u.deg))
        assert cons.get_search_condition() == "1 = CONTAINS(MOC(6, POINT(3.0, -30.0)), coverage)"
        assert cons._extra_tables == ["rr.stc_spatial"]

    def test_SkyCoord_Circle(self):
        cons = registry.Spatial((SkyCoord(3 * u.deg, -30 * u.deg), 3))
        assert cons.get_search_condition() == "1 = CONTAINS(MOC(6, CIRCLE(3.0, -30.0, 3)), coverage)"
        assert cons._extra_tables == ["rr.stc_spatial"]


class TestSpectralConstraint:
    # These tests might need some float literal fuzziness.  I'm just
    # too lazy at this point to see if pytest has something on board
    # that would be useful there.
    def test_energy_float(self):
        cons = registry.Spectral(1e-19)
        assert cons.get_search_condition() == "1e-19 BETWEEN spectral_start AND spectral_end"

    def test_energy_eV(self):
        cons = registry.Spectral(5 * u.eV)
        assert cons.get_search_condition() == "8.01088317e-19 BETWEEN spectral_start AND spectral_end"

    def test_energy_interval(self):
        cons = registry.Spectral((1e-10 * u.erg, 2e-10 * u.erg))
        assert cons.get_search_condition() == (
            "1 = ivo_interval_overlaps(spectral_start, spectral_end, 1e-17, 2e-17)")

    def test_wavelength(self):
        cons = registry.Spectral(5000 * u.Angstrom)
        assert cons.get_search_condition() == "3.9728917142978567e-19 BETWEEN spectral_start AND spectral_end"

    def test_wavelength_interval(self):
        cons = registry.Spectral((20 * u.cm, 22 * u.cm))
        assert (cons.get_search_condition()
                == "1 = ivo_interval_overlaps(spectral_start, spectral_end,"
                " 9.932229285744642e-25, 9.029299350676949e-25)")

    def test_frequency(self):
        cons = registry.Spectral(2 * u.GHz)
        assert (cons.get_search_condition()
                == "1.32521403e-24 BETWEEN spectral_start AND spectral_end")

    def test_frequency_interval(self):
        cons = registry.Spectral((88 * u.MHz, 102 * u.MHz))
        assert (cons.get_search_condition()
                == "1 = ivo_interval_overlaps(spectral_start, spectral_end,"
                " 5.830941732e-26, 6.758591553e-26)")


class TestTemporalConstraint:
    def test_plain_float(self):
        cons = registry.Temporal((54130, 54200))
        assert (cons.get_search_condition()
                == "1 = ivo_interval_overlaps(time_start, time_end, 54130, 54200)")

    def test_single_time(self):
        cons = registry.Temporal(Time('2022-01-10'))
        assert (cons.get_search_condition()
                == "59589.0 BETWEEN time_start AND time_end")

    def test_time_interval(self):
        cons = registry.Temporal((Time(2459000, format='jd'),
                                  Time(59002, format='mjd')))
        assert (cons.get_search_condition()
                == "1 = ivo_interval_overlaps(time_start, time_end, 58999.5, 59002.0)")

    def test_multi_times_rejected(self):
        with pytest.raises(ValueError) as excinfo:
            registry.Temporal(Time(['1999-01-01', '2010-01-01']))
        assert (str(excinfo.value) == "RegTAP time constraints must"
                " be made from single time instants.")


class TestWhereClauseBuilding:
    @staticmethod
    def where_clause_for(*args, **kwargs):
        cons = list(args) + rtcons.keywords_to_constraints(kwargs)
        return rtcons.build_regtap_query(cons).split("\nWHERE\n", 1)[1].split("\nGROUP BY\n")[0]

    @pytest.mark.usefixtures('messenger_vocabulary')
    def test_from_constraints(self):
        assert self.where_clause_for(
            rtcons.Waveband("EUV"),
            rtcons.Author("%Hubble%")
        ) == ("(1 = ivo_hashlist_has(rr.resource.waveband, 'euv'))\n"
              "  AND (role_name LIKE '%Hubble%' AND base_role='creator')")

    @pytest.mark.usefixtures('messenger_vocabulary')
    def test_from_keywords(self):
        assert self.where_clause_for(
            waveband="EUV",
            author="%Hubble%"
        ) == ("(1 = ivo_hashlist_has(rr.resource.waveband, 'euv'))\n"
              "  AND (role_name LIKE '%Hubble%' AND base_role='creator')")

    @pytest.mark.usefixtures('messenger_vocabulary')
    def test_mixed(self):
        assert self.where_clause_for(
            rtcons.Waveband("EUV"),
            author="%Hubble%"
        ) == ("(1 = ivo_hashlist_has(rr.resource.waveband, 'euv'))\n"
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
                                      " author, datamodel, ivoid, keywords, servicetype,"
                                      " spatial, spectral, temporal, ucd, waveband.")

    def test_with_legacy_keyword(self):
        assert self.where_clause_for(
            "plain", "string"
        ) == (
            '(ivoid IN (SELECT ivoid FROM rr.resource WHERE '
            "1=ivo_hasword(res_description, 'plain') UNION SELECT ivoid FROM rr.resource "
            "WHERE 1=ivo_hasword(res_title, 'plain') UNION SELECT ivoid FROM "
            "rr.res_subject WHERE res_subject ILIKE '%plain%'))\n"
            '  AND (ivoid IN (SELECT ivoid FROM rr.resource WHERE '
            "1=ivo_hasword(res_description, 'string') UNION SELECT ivoid FROM rr.resource "
            "WHERE 1=ivo_hasword(res_title, 'string') UNION SELECT ivoid FROM "
            "rr.res_subject WHERE res_subject ILIKE '%string%'))")


class TestSelectClause:
    def test_expected_columns(self):
        # This will break as regtap.RegistryResource.expected_columns
        # is changed.  Just update the assertion then.
        assert rtcons.build_regtap_query(
            rtcons.keywords_to_constraints({"author": "%Hubble%"})
        ).split("\nFROM\nrr.resource\n")[0] == (
            "SELECT\n"
            "ivoid, "
            "res_type, "
            "short_name, "
            "res_title, "
            "content_level, "
            "res_description, "
            "reference_url, "
            "creator_seq, "
            "content_type, "
            "source_format, "
            "source_value, "
            "region_of_regard, "
            "waveband, "
            "\n  ivo_string_agg(COALESCE(access_url, ''), ':::py VO sep:::') AS access_urls, "
            "\n  ivo_string_agg(COALESCE(standard_id, ''), ':::py VO sep:::') AS standard_ids, "
            "\n  ivo_string_agg(COALESCE(intf_type, ''), ':::py VO sep:::') AS intf_types, "
            "\n  ivo_string_agg(COALESCE(intf_role, ''), ':::py VO sep:::') AS intf_roles")

    def test_group_by_columns(self):
        # Again, this will break as regtap.RegistryResource.expected_columns
        # is changed.  Just update the assertion then.
        assert rtcons.build_regtap_query([rtcons.Author("%Hubble%")]
                                         ).split("\nGROUP BY\n")[-1] == (
            "ivoid, "
            "res_type, "
            "short_name, "
            "res_title, "
            "content_level, "
            "res_description, "
            "reference_url, "
            "creator_seq, "
            "content_type, "
            "source_format, "
            "source_value, "
            "region_of_regard, "
            "waveband")
