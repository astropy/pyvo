# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Various mixins
"""
from __future__ import (
    absolute_import, division, print_function, unicode_literals)

from functools import partial
import requests

from .query import DALServiceError
from ..tools import vosi

class AvailabilityMixin(object):
    """
    Mixing for VOSI availability
    """
    _availability = (None, None)

    @property
    def availability(self):
        """
        returns availability as a tuple in the following form:

        Returns
        -------
        [0] : bool
            whether the service is available or not
        [1] : datetime
            the time since the server is running
        """
        if self._availability == (None, None):
            avail_url = '{0}/availability'.format(self.baseurl)

            response = requests.get(avail_url, stream=True)

            try:
                response.raise_for_status()
            except requests.RequestException as ex:
                raise DALServiceError.from_except(ex, avail_url)

            # requests doesn't decode the content by default
            response.raw.read = partial(response.raw.read, decode_content=True)

            self._availability = vosi.parse_availability(response.raw)
        return self._availability

    @property
    def available(self):
        """
        True if the service is available, False otherwise
        """
        return self.availability[0]

    @property
    def up_since(self):
        """
        datetime the service was started
        """
        return self.availability[1]


class CapabilityMixin(object):
    """
    Mixing for VOSI capability
    """
    _capabilities = None

    @property
    def capabilities(self):
        """
        Returns capabilities as a nested dictionary
        """
        if self._capabilities is None:
            capa_url = '{0}/capabilities'.format(self.baseurl)
            response = requests.get(capa_url, stream=True)

            try:
                response.raise_for_status()
            except requests.RequestException as ex:
                raise DALServiceError.from_except(ex, capa_url)

            # requests doesn't decode the content by default
            response.raw.read = partial(response.raw.read, decode_content=True)

            self._capabilities = vosi.parse_capabilities(response.raw)
        return self._capabilities
