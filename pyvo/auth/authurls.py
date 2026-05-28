import collections
import logging

from . import securitymethods

__all__ = ["AuthURLs"]


class AuthURLs():
    """
    AuthURLs helps determine which security method should be used
    with a given URL.  It learns the security methods through the
    VOSI capabilities, which are passed in via update_from_capabilities.

    Three collections are used internally:

    ``full_urls``
        Exact-match entries, populated when a capability declares
        ``use="full"``. An exact match takes priority and is
        returned without consulting any other collection.

    ``_explicit_urls``
        Prefix-match entries registered by callers via
        ``add_security_method_for_url``. All matching entries are
        combined, so a registration for a base URL propagates
        to every sub-path beneath it.

    ``_capability_urls``
        Prefix-match entries loaded from VOSI capabilities
        (``use="base"``).  Only the most-specific (longest) matching
        entry is used.

    For a given URL ``allowed_auth_methods`` returns the union of:

    1. The ``full_urls`` exact match, if one exists (short-circuits).
    2. All matching ``_explicit_urls`` entries.
    3. The single most-specific matching ``_capability_urls`` entry.
    """

    def __init__(self):
        self.full_urls = collections.defaultdict(set)
        self._explicit_urls = collections.defaultdict(set)
        self._capability_urls = collections.defaultdict(set)

    def update_from_capabilities(self, capabilities):
        """
        Update the URL to security method mapping using the
        capabilities provided.

        Parameters
        ----------
        capabilities : object
            List of `~pyvo.io.vosi.voresource.Capability`
        """
        for c in capabilities:
            for i in c.interfaces:
                for u in i.accessurls:
                    url = u.content
                    exact = u.use == 'full'

                    if not i.securitymethods:
                        self._add_capability_method(url, securitymethods.ANONYMOUS, exact)

                    for sm in i.securitymethods:
                        method = sm.standardid or securitymethods.ANONYMOUS
                        self._add_capability_method(url, method, exact)

    def add_security_method_for_url(self, url, security_method, exact=False):
        """
        Add a security method for a url.
        This is additive with update_from_capabilities.  This
        can be useful to set additional security methods that
        aren't set in the capabilities for whatever reason.

        Parameters
        ----------
        url : str
            URL to set a security method for
        security_method : str
            URI of the security method to set
        exact : bool
            If True, match only this URL.  If False, match all URLs that
            start with this URL as a base.
        """
        if exact:
            self.full_urls[url].add(security_method)
        else:
            self._explicit_urls[url].add(security_method)

    def _add_capability_method(self, url, security_method, exact=False):
        """Store a security method discovered from VOSI capabilities."""
        if exact:
            self.full_urls[url].add(security_method)
        else:
            self._capability_urls[url].add(security_method)

    def allowed_auth_methods(self, url):
        """
        Return the authentication methods allowed for a particular URL.
        The methods are returned as URIs that represent security methods.

        Parameters
        ----------
        url : str
            the URL to determine authentication methods
        """
        logging.debug('Determining auth method for %s', url)

        # Exact-match entries take unconditional priority.
        if url in self.full_urls:
            methods = self.full_urls[url]
            logging.debug('Matching full url %s, methods %s', url, methods)
            return methods

        methods = set()

        # Union every matching caller-registered prefix.
        for prefix, prefix_methods in self._sorted(self._explicit_urls):
            if url.startswith(prefix):
                logging.debug(
                    'Matching explicit url %s, methods %s', prefix, prefix_methods
                )
                methods.update(prefix_methods)

        # Most-specific capability entry wins, stop at first match.
        for cap_url, cap_methods in self._sorted(self._capability_urls):
            if url.startswith(cap_url):
                logging.debug(
                    'Matching capability url %s, methods %s', cap_url, cap_methods
                )
                methods.update(cap_methods)
                break

        if methods:
            return methods

        logging.debug('No match, using anonymous auth')
        return {securitymethods.ANONYMOUS}

    def _sorted(self, url_dict):
        """Yield (url, methods) pairs from ``url_dict``, longest URL first."""
        yield from sorted(url_dict.items(), key=lambda x: len(x[0]), reverse=True)

    def __repr__(self):
        urls = []
        for url, methods in self.full_urls.items():
            urls.append('Full match:' + url + ':' + str(methods))
        for url, methods in self._sorted(self._explicit_urls):
            urls.append('Explicit match:' + url + ':' + str(methods))
        for url, methods in self._sorted(self._capability_urls):
            urls.append('Capability match:' + url + ':' + str(methods))
        return '\n'.join(urls)
