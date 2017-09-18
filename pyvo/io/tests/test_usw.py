#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.io.vosi
"""
from __future__ import (
    absolute_import, division, print_function, unicode_literals)

import unittest

from pyvo.io.uws import parse_job

from astropy.utils.data import get_pkg_data_filename

class UWSTest(unittest.TestCase):
    def test_nil(self):
        with open(get_pkg_data_filename('data/uws_nil.xml')) as fobj:
            job = parse_job(fobj)

        self.assertIsNone(job['destruction'])
