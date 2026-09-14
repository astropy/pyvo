"""Session storage with credential management for OAuth2 protected resources

This module contains the SessionStore class which manages oauth session for
a given protected resource (identified via their URL).

The intended object type of these sessions are OAuth2Session from
requests_oauthlib, and the intended storage method is via keyring.

Other Session classes can be used as long as they have a `client_id` attribute.

requests_oauthlib, keyring and a keyrings.cryptfile are all dependencies for
pyvo to ensure this all works. However if necessary other keyring backends can
be activated.
"""
import logging
import keyring

from requests_oauthlib import OAuth2Session
from pyvo.utils.http import create_session

__all__ = ["SessionStore"]


class SessionStore:
    """
    SessionStore helps determine which session should be used
    with a given URL.  Sessions are registered by callers via
    ``add_session_for_url``.

    Two collections are used internally:

    ``full_urls``
        Exact-match entries, populated when ``add_session_for_url``
        is called with ``exact=True``.  An exact match takes priority
        and is returned without consulting any other collection.

    ``_explicit_urls``
        Prefix-match entries registered with ``exact=False``, so a
        registration for a base URL propagates to every sub-path
        beneath it.  The most-specific (longest) matching entry wins.

    For a given URL ``session_for_url`` returns:

    1. The ``full_urls`` exact match, if one exists.
    2. Otherwise the single most-specific matching ``_explicit_urls`` entry.
    3. Otherwise ``None``.

    The same lookup is available through subscript access, e.g.
    ``store[url]``, which raises ``KeyError`` instead of returning
    ``None`` when no entry matches.

    Client secrets are never kept in memory by this class: they are
    delegated to the system keystore (via ``keyring``), keyed by their
    paired client ID which can be extracted from the session stored
    for a URL.
    """

    def __init__(self, keystore_name: str):
        """
        Initialize this session store

        Parameters
        ----------
        keystore_name : str
            Keystore identifier for the service using this session store.
        """
        self.keystore_name: str = keystore_name
        self.full_urls: dict[str, OAuth2Session] = {}
        self._explicit_urls: dict[str, OAuth2Session] = {}

    def add_client_secret_for_url(self, url: str, client_secret: str):
        """
        Store the client secret associated with a URL in the system
        keystore.

        Parameters
        ----------
        url : str
            URL the client secret belongs to
        client_secret : str
            the client secret to store

        Raises
        ------
        ValueError
            if the session for the URL has no ``client_id``
        """
        session = self[url]
        client_id = getattr(session, 'client_id', None)
        if client_id is None:
            raise ValueError(
                f'Session for {url} has no client_id; cannot store a client secret'
            )
        logging.debug('Storing client secret for %s in the keystore', url)
        keyring.set_password(self.keystore_name, client_id, client_secret)

    def get_client_secret_for_url(self, url: str) -> str | None:
        """
        Return the client secret stored in the system keystore for a URL,
        or ``None`` if no secret has been stored.

        Parameters
        ----------
        url : str
            URL to look up the client secret for

        Returns
        -------
        str or None
            Client secret for URL, or ``None`` if none is stored

        Raises
        ------
        ValueError
            if the session for the URL has no ``client_id``
        """
        session = self[url]
        client_id = getattr(session, 'client_id', None)
        if not client_id:
            raise ValueError(
                f'Session for {url} has no client_id; cannot look up a client secret'
            )

        client_secret = keyring.get_password(self.keystore_name, client_id)
        if client_secret is None:
            logging.debug('No client secret in the keystore for %s', url)
        return client_secret

    def delete_client_secret_for_url(self, url: str):
        """
        Remove the client secret stored in the system keystore for a URL.
        Does nothing if no secret has been stored.

        May propagate keyring.delete_password errors on failure.

        Parameters
        ----------
        url : str
            URL to remove the client secret for

        Raises
        ------
        ValueError
            if the session for the URL has no ``client_id``
        """
        session = self[url]
        client_id = getattr(session, 'client_id', None)
        if not client_id:
            raise ValueError(
                f'Session for {url} has no client_id; cannot delete a client secret'
            )
        keyring.delete_password(self.keystore_name, client_id)

    def add_session_for_url(
        self,
        url: str,
        session: OAuth2Session,
        client_secret: str | None = None,
        exact: bool = False,
    ):
        """
        Register a session object that should be used for requests directed at a
        given URL.

        The session is stored so that later requests matching the supplied URL can
        reuse the same authenticated connection. When ``exact`` is enabled the URL
        is registered as a full, literal match; otherwise it is registered as an
        explicit prefix-style entry that may also match related URLs. The session
        must expose a ``client_id`` attribute, since that value identifies the
        credentials associated with the connection. If a client secret is supplied,
        it is additionally associated with the same URL so that authentication can
        be completed later.

        Parameters
        ----------
        url : str
            URL for the session we are storing for
        session : OAuth2Session
            The session object to associate with the URL. It must provide a
            ``client_id`` attribute.
        client_secret : str, optional
            Client secret to associate with the URL. When omitted, no secret is
            stored. Can be stored at a later time using `add_client_secret_for_url`
        exact : bool, default False
            If ``True``, the URL is registered as a full exact-match entry. If
            ``False``, it is registered as an explicit entry that may match
            non-identical but related URLs.

        Raises
        ------
        ValueError
            If ``session`` does not provide a ``client_id`` attribute, which means
            the session cannot be stored.
        """
        if not hasattr(session, "client_id"):
            raise ValueError(
                f'Session for {url} has no client_id; cannot store this session'
            )
        if exact:
            self.full_urls[url] = session
        else:
            self._explicit_urls[url] = session
        if client_secret:
            self.add_client_secret_for_url(url,client_secret)

    def get_session_for_url(
        self, url: str, return_anonymous_if_not_found: bool = True
    ) -> OAuth2Session | None:
        """
        Return the session for a particular URL.

        An exact-match entry takes unconditional priority.  Otherwise the
        most-specific (longest) matching prefix entry is returned.  When no
        entry matches at all, a plain anonymous (unauthenticated) session is
        returned if ``return_anonymous_if_not_found`` is True, and ``None``
        otherwise.

        Parameters
        ----------
        url : str
            the URL to obtain a session object for
        return_anonymous_if_not_found : bool
            If True (the default), fall back to a fresh anonymous session
            when no registered entry matches the URL.  If False, return
            ``None`` instead so callers can detect the miss.
        """
        logging.debug('Determining session for %s', url)

        # Exact-match entries take unconditional priority.
        session_match = self.full_urls.get(url)
        if session_match is not None:
            logging.debug('Matching full url %s, session %s', url, session_match)
            return session_match

        # Return the most-specific matching caller-registered prefix.
        for prefix, prefix_session in self._sorted_by_url_length(self._explicit_urls):
            if url.startswith(prefix):
                logging.debug(
                    'Matching explicit url %s, session %s', prefix, prefix_session
                )
                return prefix_session

        if return_anonymous_if_not_found:
            logging.debug('No match for %s, using anonymous session', url)
            # Get generic session
            return create_session()

        logging.debug('No matching session for %s', url)
        return None

    def _sorted_by_url_length(self, url_dict):
        """
        Yield (url, session) pairs from ``url_dict``, longest URL first.

        Copied from pyvo.auth.authurls.py
        """
        yield from sorted(url_dict.items(), key=lambda x: len(x[0]), reverse=True)

    def __getitem__(self, url: str) -> OAuth2Session:
        """
        Return the session for a particular URL using subscript syntax.

        Parameters
        ----------
        url : str
            the URL to obtain a session object for

        Raises
        ------
        KeyError
            if no exact or prefix entry matches the URL
        """
        url_session = self.get_session_for_url(url, False)
        if url_session is None:
            raise KeyError(url)
        return url_session

    def __repr__(self):
        urls = []
        for url in self.full_urls:
            urls.append('Full match:' + url)
        for url, _session in self._sorted_by_url_length(self._explicit_urls):
            urls.append('Explicit match:' + url)
        return '\n'.join(urls)
