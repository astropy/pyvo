#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.io.vosi
"""
from operator import eq as equals

import pytest

import pyvo.io.vosi as vosi
import pyvo.io.vosi.vodataservice as vs
import pyvo.io.vosi.tapregext as tr
from pyvo.io.vosi.exceptions import W06

from astropy.utils.data import get_pkg_data_filename


@pytest.fixture()
def parsed_caps():
    return vosi.parse_capabilities(get_pkg_data_filename(
            "data/capabilities.xml"))


@pytest.mark.usefixtures("parsed_caps")
class TestCapabilities:
    def test_availability(self, parsed_caps):
        assert equals(
            parsed_caps[0].standardid,
            "ivo://ivoa.net/std/VOSI#availability")
        assert type(parsed_caps[0].interfaces[0]) == vs.ParamHTTP
        assert parsed_caps[0].interfaces[0].accessurls[0].use == "full"
        assert equals(
            parsed_caps[0].interfaces[0].accessurls[0].content,
            "http://example.org/tap/availability")

    def test_capendpoint(self, parsed_caps):
        assert equals(
            parsed_caps[1].standardid,
            "ivo://ivoa.net/std/VOSI#capabilities")
        assert type(parsed_caps[1].interfaces[0]) == vs.ParamHTTP
        assert parsed_caps[1].interfaces[0].accessurls[0].use == "full"
        assert equals(
            parsed_caps[1].interfaces[0].accessurls[0].content,
            "http://example.org/tap/capabilities")

    def test_tablesendpoint(self, parsed_caps):
        assert parsed_caps[2].standardid == "ivo://ivoa.net/std/VOSI#tables"
        assert type(parsed_caps[2].interfaces[0]) == vs.ParamHTTP
        assert parsed_caps[2].interfaces[0].accessurls[0].use == "full"
        assert equals(
            parsed_caps[2].interfaces[0].accessurls[0].content,
            "http://example.org/tap/tables")

    def test_type_parsed(self, parsed_caps):
        assert type(parsed_caps[3]) == tr.TableAccess

    def test_stdid_parsed(self, parsed_caps):
        assert parsed_caps[3].standardid == "ivo://ivoa.net/std/TAP"

    def test_dm_parsed(self, parsed_caps):
        assert equals(
            parsed_caps[3].datamodels[0].ivo_id,
            "ivo://ivoa.net/std/ObsCore#table-1.1")
        assert parsed_caps[3].datamodels[0].content == "Obscore-1.1"

        assert equals(
            parsed_caps[3].datamodels[1].ivo_id,
            "ivo://ivoa.net/std/RegTAP#1.0")
        assert parsed_caps[3].datamodels[1].content == "Registry 1.0"

    def test_language_parsed(self, parsed_caps):
        assert parsed_caps[3].languages[0].name == "ADQL"
        assert equals(
            parsed_caps[3].languages[0].versions[0].ivo_id,
            "ivo://ivoa.net/std/ADQL#v2.0")
        assert parsed_caps[3].languages[0].versions[0].content == "2.0"
        assert parsed_caps[3].languages[0].description == "ADQL 2.0"

    def test_udfs(self, parsed_caps):
        assert equals(
            parsed_caps[3].languages[0].languagefeaturelists[0].type,
            "ivo://ivoa.net/std/TAPRegExt#features-udf")
        assert equals(
            parsed_caps[3].languages[0].languagefeaturelists[0][0].form,
            "form 1")
        assert equals(
            parsed_caps[3].languages[0].languagefeaturelists[0][
                0].description,
            "description 1")
        assert equals(
            parsed_caps[3].languages[0].languagefeaturelists[0][1].form,
            "form 2")
        assert equals(
            parsed_caps[3].languages[0].languagefeaturelists[0].features[
                1].description,
            "description 2")

    def test_adqlgeos(self, parsed_caps):
        assert equals(
            parsed_caps[3].languages[0].languagefeaturelists[1].type,
            "ivo://ivoa.net/std/TAPRegExt#features-adqlgeo")
        assert equals(
            parsed_caps[3].languages[0].languagefeaturelists[1].features[
                0].form,
            "BOX")
        assert equals(
            parsed_caps[3].languages[0].languagefeaturelists[1].features[
                1].form,
            "POINT")

    def test_outputformats(self, parsed_caps):
        assert equals(
            parsed_caps[3].outputformats[0].ivo_id,
            "ivo://ivoa.net/std/TAPRegExt#output-votable-binary")
        assert parsed_caps[3].outputformats[0].mime == "text/xml"

        assert parsed_caps[3].outputformats[1].ivo_id is None
        assert parsed_caps[3].outputformats[1].mime == "text/html"

    def test_uploadmethods(self, parsed_caps):
        assert equals(
            parsed_caps[3].uploadmethods[0].ivo_id,
            "ivo://ivoa.net/std/TAPRegExt#upload-https")
        assert equals(
            parsed_caps[3].uploadmethods[1].ivo_id,
            "ivo://ivoa.net/std/TAPRegExt#upload-inline")

    def test_temporal_limits(self, parsed_caps):
        assert parsed_caps[3].retentionperiod.default == 172800
        assert parsed_caps[3].executionduration.default == 3600

    def test_spatial_limits(self, parsed_caps):
        assert parsed_caps[3].outputlimit.default.unit == "row"
        assert parsed_caps[3].outputlimit.default.content == 2000

        assert parsed_caps[3].outputlimit.hard.unit == "row"
        assert parsed_caps[3].outputlimit.hard.content == 10000000

        assert parsed_caps[3].uploadlimit.hard.unit == "byte"
        assert parsed_caps[3].uploadlimit.hard.content == 100000000

    def test_multiple_capa_descriptions(self):
        with pytest.warns(W06):
            vosi.parse_capabilities(get_pkg_data_filename(
                'data/capabilities/multiple_capa_descriptions.xml'))

        with pytest.raises(W06):
            vosi.parse_capabilities(get_pkg_data_filename(
                'data/capabilities/multiple_capa_descriptions.xml'),
                pedantic=True)


@pytest.mark.usefixtures("parsed_caps")
class TestInterface:
    def test_interface_parsed(self, parsed_caps):
        assert parsed_caps[3].interfaces[0].accessurls[0].use == "base"
        assert equals(
            parsed_caps[3].interfaces[0].accessurls[0].content,
            "http://example.org/tap")

    def test_mirrors_parsed(self, parsed_caps):
        assert len(parsed_caps[3].interfaces[0].mirrorurls) == 2

    def test_mirrors_have_titles(self, parsed_caps):
        assert [m.title for m in parsed_caps[3].interfaces[0].mirrorurls
            ] == ["https version", "Paris mirror"]

    def test_mirrors_have_urls(self, parsed_caps):
        assert [m.content for m in parsed_caps[3].interfaces[0].mirrorurls
            ] == ['https://example.org/tap', 'https://paris.example.org/tap']

    def test_testquerystring_parsed(self, parsed_caps):
        assert (parsed_caps[3].interfaces[0].testquerystring.content
            == 'QUERY=SELECT%20*%20FROM%20tap_schema.tables&LANG=ADQL')
