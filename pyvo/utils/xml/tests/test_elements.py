#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.utils.xml.elements
"""

import io
import pytest

from astropy.utils.xml import iterparser

from pyvo.utils.xml import elements


class TBase(elements.ElementWithXSIType):
    pass


@TBase.register_xsi_type("foo:TOther1")
class TOther1(TBase):
    pass


# it's unclear whether we want to support unprefixed type names
# once we properly handle XML namespaces.  Feel free to adapt
# the following declaration.
@TBase.register_xsi_type("TOther2")
class TOther2(TBase):
    pass


class _Root(elements.Element):
    def __init__(self):
        super().__init__(self, _name="root")
        self._tbase = None

    @elements.xmlelement(name="tbase", cls=TBase)
    def tbase(self):
        return self._tbase

    @tbase.setter
    def tbase(self, obj):
        self._tbase = obj


class TestXSIType:
    # Note: most of these tests will need namespace declarations
    # once we're properly dealing with namespaces.  However, I
    # don't want to predicate an API to proper namespace support,
    # so they're missing for now.
    def _parse_string(self, xml_source):
        with iterparser.get_xml_iterator(io.BytesIO(xml_source)) as i:
            return _Root().parse(i, {})

    def test_no_type(self):
        found_type = self._parse_string(b'<tbase/>').tbase.__class__
        assert found_type.__name__ == "TBase"

    def test_prefixed_type(self):
        found_type = self._parse_string(b'<tbase xsi:type="foo:TOther1"/>'
                                        ).tbase.__class__
        assert found_type.__name__ == "TOther1"

    def test_unprefixed_type(self):
        # This is undesired behaviour; this test should fail once
        # we've properly parsing XML
        found_type = self._parse_string(b'<tbase xsi:type="TOther1"/>'
                                        ).tbase.__class__
        assert found_type.__name__ == "TOther1"

    def test_badprefixed_type(self):
        found_type = self._parse_string(b'<tbase xsi:type="ns1:TOther2"/>'
                                        ).tbase.__class__
        assert found_type.__name__ == "TOther2"

    def test_xsi_ignorable(self):
        # This is again unwelcome behaviour, but unavoidable as long
        # as we hack around namespaces
        found_type = self._parse_string(b'<tbase type="ns1:TOther2"/>'
                                        ).tbase.__class__
        assert found_type.__name__ == "TOther2"

    def test_xsi_preferred(self):
        # Another piece unwelcome behaviour.
        found_type = self._parse_string(
            b'<tbase foo:type="TOther1" xsi:type="ns1:TOther2"/>'
        ).tbase.__class__
        assert found_type.__name__ == "TOther2"

    def test_bad_type(self):
        with pytest.warns(match='Unknown xsi:type ns1:NoSuchType ignored'):
            self._parse_string(b'<tbase xsi:type="ns1:NoSuchType"/>')
