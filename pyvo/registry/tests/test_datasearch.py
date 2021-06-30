#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.registry.datasearch
"""

import datetime

import numpy
import pytest

from pyvo.registry import datasearch


class TestAbstractConstraint:
    def test_no_search_condition(self):
        with pytest.raises(NotImplementedError):
            datasearch.Constraint().get_search_condition()



class TestSQLLiterals:
    @pytest.fixture(scope="class", autouse=True)
    def literals(self):
        class _WithFillers(datasearch.Constraint):
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
            datasearch.make_sql_literal({})
        assert str(excinfo.value) == "Cannot format {} as a SQL literal"


class TestFreetextConstraint:
    def test_basic(self):
        assert (datasearch.Freetext("star").get_search_condition()
            == "1=ivo_hasword(res_description, 'star')"
            " OR 1=ivo_hasword(res_title, 'star')"
            " OR 1=ivo_hasword(role_name, 'star')")

    def test_interesting_literal(self):
        assert (datasearch.Freetext("α Cen's planets").get_search_condition()
            == "1=ivo_hasword(res_description, 'α Cen''s planets')"
            " OR 1=ivo_hasword(res_title, 'α Cen''s planets')"
            " OR 1=ivo_hasword(role_name, 'α Cen''s planets')")


class TestAuthorConstraint:
    def test_basic(self):
        assert (datasearch.Author("%Hubble%").get_search_condition()
            == "role_name LIKE '%Hubble%' AND base_role='creator'")

