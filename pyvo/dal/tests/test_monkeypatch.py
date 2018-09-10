#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.dal.datalink
"""
from __future__ import (
    absolute_import, division, print_function, unicode_literals)

from astropy.table import Table
from astropy.utils.data import get_pkg_data_filename


def test_monkeypatch():
    Table.read(get_pkg_data_filename("data/monkeypatch.xml"))
    import pyvo
    Table.read(get_pkg_data_filename("data/monkeypatch.xml"))
