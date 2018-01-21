# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
VOSI mixins
"""
from __future__ import (
    absolute_import, division, print_function, unicode_literals)

from itertools import chain
import requests

from astropy.utils.decorators import lazyproperty

from .query import VOSITables

from .exceptions import DALServiceError
from ..io import vosi
from ..utils.url import url_sibling
from ..utils.decorators import stream_decode_content

__all__ = ['AvailabilityMixin', 'CapabilityMixin']


class AvailabilityMixin(object):
    """
    Mixing for VOSI availability
    """
    @stream_decode_content
    def _availability(self):
        """
        Service Availability as a
        :py:class:`~pyvo.io.vosi.availability.Availability` object
        """
        avail_url = '{0}/availability'.format(self.baseurl)

        response = requests.get(avail_url, stream=True)

        try:
            response.raise_for_status()
        except requests.RequestException as ex:
            raise DALServiceError.from_except(ex, avail_url)

        return response.raw

    @lazyproperty
    def availability(self):
        return vosi.parse_availability(self._availability().read)

    @property
    def available(self):
        """
        True if the service is available, False otherwise
        """
        return self.availability.available

    @property
    def up_since(self):
        """
        datetime the service was started
        """
        return self.availability.upsince


class CapabilityMixin(object):
    """
    Mixing for VOSI capability
    """
    @stream_decode_content
    def _capabilities(self):
        """
        Returns capabilities as a
        py:class:`~pyvo.io.vosi.availability.Availability` object
        """
        capa_urls = [
            '{0}/capabilities'.format(self.baseurl),
            url_sibling(self.baseurl, 'capabilities')
        ]

        for capa_url in capa_urls:
            try:
                response = requests.get(capa_url, stream=True)
                response.raise_for_status()
                break
            except requests.RequestException:
                continue
        else:
            raise DALServiceError("No working capabilities endpoint provided")

        return response.raw

    @lazyproperty
    def capabilities(self):
        return vosi.parse_capabilities(self._capabilities().read)


class TablesMixin(CapabilityMixin):
    """
    Mixin for VOSI tables
    """
    @stream_decode_content
    def _tables(self):
        try:
            interfaces = next(
                _ for _ in self.capabilities if _.standardid.startswith(
                    'ivo://ivoa.net/std/VOSI#tables')
            ).interfaces
            accessurls = chain.from_iterable(_.accessurls for _ in interfaces)
            tables_urls = (_.value for _ in accessurls)
        except StopIteration:
            tables_urls = [
                '{0}/tables'.format(self.baseurl),
                url_sibling(self.baseurl, 'tables')
            ]

        for tables_url in tables_urls:
            try:
                response = requests.get(tables_url, stream=True)
                response.raise_for_status()
                break
            except requests.RequestException:
                continue
        else:
            raise DALServiceError("No working tables endpoint provided")

        return response.raw

    @lazyproperty
    def tables(self):
        return VOSITables(vosi.parse_tables(self._tables().read))
