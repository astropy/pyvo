# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
VOSI classes and mixins
"""
from itertools import chain
import requests
from urllib.parse import urlparse

from astropy.utils.decorators import lazyproperty, deprecated

from .exceptions import DALServiceError
from ..io import vosi
from ..utils.url import url_sibling
from ..utils.decorators import stream_decode_content, response_decode_content
from ..utils.http import use_session

__all__ = ['CapabilityMixin', 'VOSITables']


class EndpointMixin:
    def _get_endpoint_candidates(self, endpoint):
        """Construct endpoint URLs from base URL and endpoint"""
        urlcomp = urlparse(self.baseurl)
        # Include the port number if present
        netloc = urlcomp.hostname
        if urlcomp.port:
            netloc += f':{urlcomp.port}'
        curated_baseurl = f'{urlcomp.scheme}://{netloc}{urlcomp.path}'

        if not endpoint:
            raise AttributeError('endpoint required')

        return [f'{curated_baseurl}/{endpoint}', url_sibling(curated_baseurl, endpoint)]

    @staticmethod
    def _build_error_message(endpoint, attempted_urls):
        """Build error message from attempted URLs and their failures"""
        return (
            f"Unable to access the {endpoint} endpoint at:\n"
            f"{chr(10).join(attempted_urls)}\n\n"
            f"This could mean:\n"
            f"1. The service URL is incorrect\n"
            f"2. The service is temporarily unavailable\n"
            f"3. The service doesn't support this protocol\n"
            f"4. If a 503 was encountered, retry after the suggested delay.\n"
        )

    @staticmethod
    def _get_response_body(response):
        """Extract response body for error messagess"""

        max_length = 500
        # Truncate if too long (500 chars), to avoid overwhelming the user
        if response is None or not response.headers.get("Content-Type",
                                                        "").startswith("text"):
            return ""

        return f" Response body: {response.text[:max_length]}"

    def _handle_http_error(self, error, url, attempted_urls):
        """Handle HTTP errors and update attempted_urls list"""

        response_body = self._get_response_body(error.response)

        if error.response.status_code == 503:
            # Handle Retry-After header, if present
            retry_after = None
            for header in error.response.headers:
                if header.lower() == 'retry-after':
                    retry_after = error.response.headers[header]
                    break

            if retry_after:
                attempted_urls.append(
                    f"- {url}: 503 Service Unavailable (Retry-After: "
                    f"{retry_after}){response_body}")
                return True
        elif error.response.status_code == 404:
            attempted_urls.append(f"- {url}: 404 Not Found")
            return True

        status_code = error.response.status_code
        attempted_urls.append(
            f"- {url}: HTTP Code: {status_code} "
            f"{error.response.reason}{response_body}")
        return False

    def _get_endpoint(self, endpoint):
        """Attempt to connect to service endpoint"""
        attempted_urls = []
        try:
            candidates = self._get_endpoint_candidates(endpoint)
        except (ValueError, AttributeError) as e:
            raise DALServiceError(
                f"Cannot construct endpoint URL from base '{self.baseurl}' and endpoint '{endpoint}'. "
                f"{type(e).__name__}: {str(e)}"
            ) from e

        for ep_url in candidates:
            try:
                response = self._session.get(ep_url, stream=True)
                response.raise_for_status()
                return response.raw
            except requests.HTTPError as e:
                if not self._handle_http_error(e, ep_url, attempted_urls):
                    break
            except requests.ConnectionError:
                attempted_urls.append(
                    f"- {ep_url}: Connection failed "
                    f"(Possible causes: incorrect URL, DNS issue, or service is down)")
                break
            except requests.Timeout:
                attempted_urls.append(
                    f"- {ep_url}: Request timed out (Service may be overloaded or slow)")
            except (requests.RequestException, Exception) as e:
                attempted_urls.append(f"- {ep_url}: {str(e)}")
                break

        raise DALServiceError(
            self._build_error_message(endpoint, attempted_urls))


@deprecated(since="1.5")
class AvailabilityMixin(EndpointMixin):
    """
    Mixing for VOSI availability
    """
    @deprecated(since="1.5")
    @stream_decode_content
    def _availability(self):
        """
        Service Availability as a
        :py:class:`~pyvo.io.vosi.availability.Availability` object
        """
        return self._get_endpoint('availability')

    @lazyproperty
    @deprecated(since="1.5")
    def availability(self):
        return vosi.parse_availability(self._availability().read)

    @property
    @deprecated(since="1.5")
    def available(self):
        """
        True if the service is available, False otherwise
        """
        return self.availability.available

    @property
    @deprecated(since="1.5")
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
        Retrieve the raw capabilities document from the service.
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
                f'{self.baseurl}/tables',
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

    def __init__(self, vosi_tables, endpoint_url, *, session=None):
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

    def __contains__(self, tablename):
        return tablename in self.keys()

    def _get_table(self, name):
        if name in self._cache:
            return self._cache[name]

        table = self._vosi_tables.get_table_by_name(name)

        if not table.columns and not table.foreignkeys:
            tables_url = f'{self._endpoint_url}/{name}'
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
