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


class TestCapabilities:
    def test_all(self):
        capabilities = vosi.parse_capabilities(get_pkg_data_filename(
            "data/capabilities.xml"))

        assert equals(
            capabilities[0].standardid,
            "ivo://ivoa.net/std/VOSI#availability")
        assert type(capabilities[0].interfaces[0]) == vs.ParamHTTP
        assert capabilities[0].interfaces[0].accessurls[0].use == "full"
        assert equals(
            capabilities[0].interfaces[0].accessurls[0].content,
            "http://example.org/tap/availability")

        assert equals(
            capabilities[1].standardid,
            "ivo://ivoa.net/std/VOSI#capabilities")
        assert type(capabilities[1].interfaces[0]) == vs.ParamHTTP
        assert capabilities[1].interfaces[0].accessurls[0].use == "full"
        assert equals(
            capabilities[1].interfaces[0].accessurls[0].content,
            "http://example.org/tap/capabilities")

        assert capabilities[2].standardid == "ivo://ivoa.net/std/VOSI#tables"
        assert type(capabilities[2].interfaces[0]) == vs.ParamHTTP
        assert capabilities[2].interfaces[0].accessurls[0].use == "full"
        assert equals(
            capabilities[2].interfaces[0].accessurls[0].content,
            "http://example.org/tap/tables")

        assert type(capabilities[3]) == tr.TableAccess
        assert capabilities[3].standardid == "ivo://ivoa.net/std/TAP"
        assert capabilities[3].interfaces[0].accessurls[0].use == "base"
        assert equals(
            capabilities[3].interfaces[0].accessurls[0].content,
            "http://example.org/tap")

        assert equals(
            capabilities[3].datamodels[0].ivo_id,
            "ivo://ivoa.net/std/ObsCore#table-1.1")
        assert capabilities[3].datamodels[0].content == "Obscore-1.1"

        assert equals(
            capabilities[3].datamodels[1].ivo_id,
            "ivo://ivoa.net/std/RegTAP#1.0")
        assert capabilities[3].datamodels[1].content == "Registry 1.0"

        assert capabilities[3].languages[0].name == "ADQL"
        assert equals(
            capabilities[3].languages[0].versions[0].ivo_id,
            "ivo://ivoa.net/std/ADQL#v2.0")
        assert capabilities[3].languages[0].versions[0].content == "2.0"
        assert capabilities[3].languages[0].description == "ADQL 2.0"

        assert equals(
            capabilities[3].languages[0].languagefeaturelists[0].type,
            "ivo://ivoa.net/std/TAPRegExt#features-udf")
        assert equals(
            capabilities[3].languages[0].languagefeaturelists[0][0].form,
            "form 1")
        assert equals(
            capabilities[3].languages[0].languagefeaturelists[0][
                0].description,
            "description 1")
        assert equals(
            capabilities[3].languages[0].languagefeaturelists[0][1].form,
            "form 2")
        assert equals(
            capabilities[3].languages[0].languagefeaturelists[0].features[
                1].description,
            "description 2")

        assert equals(
            capabilities[3].languages[0].languagefeaturelists[1].type,
            "ivo://ivoa.net/std/TAPRegExt#features-adqlgeo")
        assert equals(
            capabilities[3].languages[0].languagefeaturelists[1].features[
                0].form,
            "BOX")
        assert equals(
            capabilities[3].languages[0].languagefeaturelists[1].features[
                1].form,
            "POINT")

        assert equals(
            capabilities[3].outputformats[0].ivo_id,
            "ivo://ivoa.net/std/TAPRegExt#output-votable-binary")
        assert capabilities[3].outputformats[0].mime == "text/xml"

        assert capabilities[3].outputformats[1].ivo_id is None
        assert capabilities[3].outputformats[1].mime == "text/html"

        assert equals(
            capabilities[3].uploadmethods[0].ivo_id,
            "ivo://ivoa.net/std/TAPRegExt#upload-https")
        assert equals(
            capabilities[3].uploadmethods[1].ivo_id,
            "ivo://ivoa.net/std/TAPRegExt#upload-inline")

        assert capabilities[3].retentionperiod.default == 172800
        assert capabilities[3].executionduration.default == 3600

        assert capabilities[3].outputlimit.default.unit == "row"
        assert capabilities[3].outputlimit.default.content == 2000

        assert capabilities[3].outputlimit.hard.unit == "row"
        assert capabilities[3].outputlimit.hard.content == 10000000

        assert capabilities[3].uploadlimit.hard.unit == "byte"
        assert capabilities[3].uploadlimit.hard.content == 100000000

    def test_multiple_capa_descriptions(self):
        with pytest.warns(W06):
            vosi.parse_capabilities(get_pkg_data_filename(
                'data/capabilities/multiple_capa_descriptions.xml'))

        with pytest.raises(W06):
            vosi.parse_capabilities(get_pkg_data_filename(
                'data/capabilities/multiple_capa_descriptions.xml'),
                pedantic=True)
