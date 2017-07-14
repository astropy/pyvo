# Licensed under a 3-clause BSD style license - see LICENSE.rst
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from astropy.extern import six

from astropy.utils.collections import HomogeneousList
from astropy.utils.xml import check as xml_check
from astropy.io.votable.exceptions import vo_raise, vo_warn, warn_or_raise

from .util import (
    make_add_simplecontent, make_add_complexcontent, Element, ValueMixin)
from . import voresource as vr
from .exceptions import W32, W33, W34, W35

__all__ = ["Availability"]

######################################################################
# FACTORY FUNCTIONS
def _convert_boolean(value, default=None):
    return {
        'false': False,
        '0': False,
        'true': True,
        '1': True
    }.get(value, default)

######################################################################
# ELEMENT CLASSES
class Availability(Element):
    def __init__(self, config=None, pos=None, **kwargs):
        super(Availability, self).__init__(config=config, pos=pos, **kwargs)

        self._tag_mapping.update({
            "available": make_add_simplecontent(
                self, "available", "available", W32),
            "upSince": make_add_simplecontent(self, "upSince", "upsince", W33),
            "downAt": make_add_simplecontent(self, "downAt", "downat", W34),
            "backAt": make_add_simplecontent(self, "backAt", "backat", W35),
            "note": make_add_simplecontent(self, "note", "notes")
        })

        self._available = None
        self._upsince = None
        self._downat = None
        self._backat = None
        self._notes = HomogeneousList(six.text_type)

    @property
    def available(self):
        return self._available

    @available.setter
    def available(self, available):
        self._available = _convert_boolean(available)

    @property
    def upsince(self):
        return self._upsince

    @upsince.setter
    def upsince(self, upsince):
        self._upsince = upsince

    @property
    def downat(self):
        return self._downat

    @downat.setter
    def downat(self, downat):
        self._downat = downat

    @property
    def backat(self):
        return self._backat

    @backat.setter
    def backat(self, backat):
        self._backat = backat

    @property
    def notes(self):
        return self._notes
