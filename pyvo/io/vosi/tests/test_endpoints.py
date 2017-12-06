#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.io.vosi
"""
from __future__ import (
    absolute_import, division, print_function, unicode_literals)

import unittest

import pyvo.io.vosi as vosi
import pyvo.io.vosi.vodataservice as vs
import pyvo.io.vosi.voresource as vr
import pyvo.io.vosi.tapregext as tr
from astropy.utils.data import get_pkg_data_filename

class VOSITest(unittest.TestCase):
    def test_availability(self):
        availability = vosi.parse_availability(get_pkg_data_filename(
            "data/availability.xml"))

        self.assertEqual(availability.available, True)
        self.assertEqual(availability.upsince, "2000-00-00T00:00:00Z")
        self.assertEqual(availability.downat, "2666-00-00T00:00:00Z")
        self.assertEqual(availability.backat, "2666-23-23T13:37:00Z")
        self.assertIn("foo", availability.notes)
        self.assertIn("bar", availability.notes)

    def test_capabilities(self):
        capabilities = vosi.parse_capabilities(get_pkg_data_filename(
            "data/capabilities.xml"))

        self.assertEqual(
            capabilities[0].standardid, "ivo://ivoa.net/std/VOSI#availability")
        self.assertEqual(
            type(capabilities[0].interfaces[0]), vs.ParamHTTP)
        self.assertEqual(
            capabilities[0].interfaces[0].accessurls[0].use, "full")
        self.assertEqual(
            capabilities[0].interfaces[0].accessurls[0].value,
            "http://example.org/tap/availability")

        self.assertEqual(
            capabilities[1].standardid, "ivo://ivoa.net/std/VOSI#capabilities")
        self.assertEqual(
            type(capabilities[1].interfaces[0]), vs.ParamHTTP)
        self.assertEqual(
            capabilities[1].interfaces[0].accessurls[0].use, "full")
        self.assertEqual(
            capabilities[1].interfaces[0].accessurls[0].value,
            "http://example.org/tap/capabilities")

        self.assertEqual(
            capabilities[2].standardid, "ivo://ivoa.net/std/VOSI#tables")
        self.assertEqual(
            type(capabilities[2].interfaces[0]), vs.ParamHTTP)
        self.assertEqual(
            capabilities[2].interfaces[0].accessurls[0].use, "full")
        self.assertEqual(
            capabilities[2].interfaces[0].accessurls[0].value,
            "http://example.org/tap/tables")

        self.assertEqual(
            type(capabilities[3]), tr.TableAccess)
        self.assertEqual(
            capabilities[3].standardid, "ivo://ivoa.net/std/TAP")
        self.assertEqual(
            capabilities[3].interfaces[0].accessurls[0].use, "base")
        self.assertEqual(
            capabilities[3].interfaces[0].accessurls[0].value,
            "http://example.org/tap")

        self.assertEqual(
            capabilities[3].datamodels[0].ivo_id,
            "ivo://ivoa.net/std/ObsCore#table-1.1")
        self.assertEqual(
            capabilities[3].datamodels[0].value, "Obscore-1.1")

        self.assertEqual(
            capabilities[3].datamodels[1].ivo_id,
            "ivo://ivoa.net/std/RegTAP#1.0")
        self.assertEqual(
            capabilities[3].datamodels[1].value, "Registry 1.0")

        self.assertEqual(capabilities[3].languages[0].name, "ADQL")
        self.assertEqual(
            capabilities[3].languages[0].versions[0].ivo_id,
            "ivo://ivoa.net/std/ADQL#v2.0")
        self.assertEqual(capabilities[3].languages[0].versions[0].value, "2.0")
        self.assertEqual(capabilities[3].languages[0].description, "ADQL 2.0")

        self.assertEqual(
            capabilities[3].languages[0].languagefeaturelists[0].type,
            "ivo://ivoa.net/std/TAPRegExt#features-udf")
        self.assertEqual(
            capabilities[3].languages[0].languagefeaturelists[0].features[
                0].form,
            "form 1")
        self.assertEqual(
            capabilities[3].languages[0].languagefeaturelists[0].features[
                0].description,
            "description 1")
        self.assertEqual(
            capabilities[3].languages[0].languagefeaturelists[0].features[
                1].form,
            "form 2")
        self.assertEqual(
            capabilities[3].languages[0].languagefeaturelists[0].features[
                1].description,
            "description 2")

        self.assertEqual(
            capabilities[3].languages[0].languagefeaturelists[1].type,
            "ivo://ivoa.net/std/TAPRegExt#features-adqlgeo")
        self.assertEqual(
            capabilities[3].languages[0].languagefeaturelists[1].features[
                0].form,
            "BOX")
        self.assertEqual(
            capabilities[3].languages[0].languagefeaturelists[1].features[
                1].form,
            "POINT")

        self.assertEqual(
            capabilities[3].outputformats[0].ivo_id,
            "ivo://ivoa.net/std/TAPRegExt#output-votable-binary")
        self.assertEqual(
            capabilities[3].outputformats[0].mime, "text/xml")

        self.assertEqual(
            capabilities[3].outputformats[1].ivo_id, None)
        self.assertEqual(
            capabilities[3].outputformats[1].mime, "text/html")

        self.assertEqual(
            capabilities[3].uploadmethods[0].ivo_id,
            "ivo://ivoa.net/std/TAPRegExt#upload-https")
        self.assertEqual(
            capabilities[3].uploadmethods[1].ivo_id,
            "ivo://ivoa.net/std/TAPRegExt#upload-inline")

        self.assertEqual(capabilities[3].retentionperiod.default, 172800)
        self.assertEqual(capabilities[3].executionduration.default, 3600)

        self.assertEqual(capabilities[3].outputlimit.default.unit, "row")
        self.assertEqual(capabilities[3].outputlimit.default.value, 2000)

        self.assertEqual(capabilities[3].outputlimit.hard.unit, "row")
        self.assertEqual(capabilities[3].outputlimit.hard.value, 10000000)

        self.assertEqual(capabilities[3].uploadlimit.hard.unit, "byte")
        self.assertEqual(capabilities[3].uploadlimit.hard.value, 100000000)

    def test_tables(self):
        tables = list(vosi.parse_tables(get_pkg_data_filename(
            "data/tables.xml")).iter_tables())

        table = tables[0]

        self.assertEqual(table.name, "test.all")
        self.assertEqual(table.title, "Test table")
        self.assertEqual(table.description, "All test data in one table")
        self.assertEqual(table.utype, "utype")

        col = table.columns[0]
        fkc = table.foreignkeys[0]

        self.assertEqual(col.name, "id")
        self.assertEqual(col.description, "Primary key")
        self.assertEqual(col.unit, "unit")
        self.assertEqual(col.ucd, "meta.id;meta.main")
        self.assertEqual(col.utype, "utype")
        self.assertEqual(type(col.datatype), vs.TAPType)
        self.assertEqual(col.datatype.arraysize, "*")
        self.assertEqual(col.datatype.size, "42")
        self.assertEqual(col.datatype.value, "VARCHAR")
        self.assertIn("indexed", col.flags)
        self.assertIn("primary", col.flags)

        self.assertEqual(fkc.targettable, "test.foreigntable")
        self.assertEqual(fkc.fkcolumns[0].fromcolumn, "testkey")
        self.assertEqual(fkc.fkcolumns[0].targetcolumn, "testkey")
        self.assertEqual(fkc.description, "Test foreigner")
        self.assertEqual(fkc.utype, "utype")
