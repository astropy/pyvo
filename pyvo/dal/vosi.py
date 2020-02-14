# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
VOSI classes and mixins
"""
from itertools import chain
import requests

from astropy.utils.decorators import lazyproperty

from .exceptions import DALServiceError
from ..io import vosi
from ..utils.url import url_sibling
from ..utils.decorators import stream_decode_content, response_decode_content
from ..utils.http import use_session

__all__ = [
    'AvailabilityMixin', 'CapabilityMixin', 'VOSITables']


class EndpointMixin():
    def _get_endpoint(self, endpoint):
        # finds the endpoint relative to the base url or its parent
        # and returns its content in raw format
        if not endpoint:
            raise AttributeError('endpoint required')
        ep_urls = [
            '{baseurl}/{endpoint}'.format(baseurl=self.baseurl,
                                          endpoint=endpoint),
            url_sibling(self.baseurl, endpoint)
        ]

        for ep_url in ep_urls:
            try:
                response = self._session.get(ep_url, stream=True)
                response.raise_for_status()
                break
            except requests.RequestException:
                continue
        else:
            raise DALServiceError(
                "No working {endpoint} endpoint provided".format(
                    endpoint=endpoint))

        return response.raw


class AvailabilityMixin(EndpointMixin):
    """
    Mixing for VOSI availability
    """
    @stream_decode_content
    def _availability(self):
        """
        Service Availability as a
        :py:class:`~pyvo.io.vosi.availability.Availability` object
        """
        return self._get_endpoint('availability')

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


class CapabilityMixin(EndpointMixin):
    """
    Mixing for VOSI capability
    """
    @stream_decode_content
    def _capabilities(self):
        """
        Returns capabilities as a
        py:class:`~pyvo.io.vosi.availability.Availability` object
        """
        return self._get_endpoint('capabilities')

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
                '{}/tables'.format(self.baseurl),
                url_sibling(self.baseurl, 'tables')
            ]

        for tables_url in tables_urls:
            try:
                response = self._session.get(tables_url, stream=True)
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


class VOSITables:
    """
    This class encapsulates access to the VOSITables using a given Endpoint.
    Access to table names is like accessing dictionary keys. using iterator
    syntax or `keys()`
    """
    def __init__(self, vosi_tables, endpoint_url, session=None):
        self._vosi_tables = vosi_tables
        self._endpoint_url = endpoint_url
        self._cache = {}
        self._session = use_session(session)

    def __len__(self):
        return self._vosi_tables.ntables

    def __getitem__(self, key):
        return self._get_table(key)

    def __iter__(self):
        for tablename in self.keys():
            yield self._get_table(tablename)

    def _get_table(self, name):
        if name in self._cache:
            return self._cache[name]

        table = self._vosi_tables.get_table_by_name(name)

        if not table.columns and not table.foreignkeys:
            tables_url = '{}/{}'.format(self._endpoint_url, name)
            response = self._get_table_file(tables_url)

            try:
                response.raise_for_status()
            except requests.RequestException as ex:
                raise DALServiceError.from_except(ex, tables_url)

            table = vosi.parse_tables(response.raw.read).get_first_table()
            self._cache[name] = table

        return table

    @response_decode_content
    def _get_table_file(self, tables_url):
        return self._session.get(tables_url, stream=True)

    def keys(self):
        """
        Iterates over the keys (table names).
        """
        for table in self._vosi_tables.iter_tables():
            yield table.name

    def values(self):
        """
        Iterates over the values (tables).
        Gathers missing values from endpoint if necessary.
        """
        for name in self.keys():
            yield self._get_table(name)

    def items(self):
        """
        Iterates over keys and values (table names and tables).
        Gathers missing values from endpoint if necessary.
        """
        for name in self.keys():
            yield (name, self._get_table(name))

    def describe(self):
        for table in self:
            table.describe()
