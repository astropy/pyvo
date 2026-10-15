"""OAuth 2.0 session handling for VO network requests using VOAuthSession.

An attempt has been made to be compatible with the existing
:py:class:`~pyvo.auth.authsession.AuthSession`, aside from support for
/capabilities as the authorization methods are retrieved differently.

Authentication may require user interaction, for instance when the device
authorization grant asks the user to visit a verification URL and enter a user
code.

TODO: Only device_code grant type is supported at this stage: to introduce other
    grant types over time. GRANT_TO_CLIENT_CLASS has those mappable to existing
    oauthlib client types.
"""
import logging
import time
from typing import Collection, List

import requests
# Oauthlib imports. Raise ImportError if not installed
try:
    from oauthlib.oauth2 import (
        DeviceClient,
        ServerError,
        UnsupportedGrantTypeError,
        OAuth2Error,
    )
    from oauthlib.oauth2.rfc6749.errors import CustomOAuth2Error
    from requests import Response
    from requests_oauthlib import OAuth2Session
except ImportError as exc:
    raise ImportError(
        "OAuth 2 Session support requires packages requests-oauthlib and keyring with a compatible "
        "backend. Install with pip install pyvo[oauth2]"
    ) from exc

from .sessionstore import SessionStore

__all__ = ["VOAuthSession"]

# Service name used to namespace entries in the system keystore.
DEFAULT_KEYSTORE_SERVICE_NAME = 'pyvo.auth.oauth2'

# Module level logger used to report authentication diagnostics.
log = logging.getLogger(__name__)

GRANT_TO_CLIENT_CLASS = {
    # TODO: Introduce and test with other grant methods
    # 'authorization_code': WebApplicationClient,
    # 'implicit': MobileApplicationClient,
    # 'urn:ietf:params:oauth:grant-type:jwt-bearer' : ServiceApplicationClient,
    # 'client_credentials': BackendApplicationClient,
    'urn:ietf:params:oauth:grant-type:device_code': DeviceClient,
}


class VOAuthSession:
    """
    A requests-like session for pyvo able to store and use different sessions
    depending on the resource
    """

    def __init__(
        self,
        grant_types: Collection[str] | None = None,
        client_name: str | None = None,
        scope: Collection[str] | str | None = None,
        keystore_name: str = DEFAULT_KEYSTORE_SERVICE_NAME,
    ) -> None:
        """
        Intialize the VOAuthSession

        Parameters
        ----------
        grant_types : collection of str, optional
            Grant types that can be used to authenticate this VOAuthSession.
            When ``None``, the grant types advertised by the authorization
            server are used. See ``_resolve_grant_types``.
        client_name : str, optional
            Name of the client of this VOAuthSession. Used during dynamic
            registration. See ``get_dynamic_client_credentials``
        scope : collection of str or str, optional
            Scopes to request when fetching a token, either as a space
            separated string or as a collection of scope names. When ``None``,
            the scopes advertised by the authorization server are used.
            See ``_resolve_scopes``.
        keystore_name : str, optional
            Service name used to namespace entries in the system keystore.
            Defaults to 'pyvo.auth.oauth2'.
        """
        super().__init__()
        self.grant_types = grant_types
        self.client_name = client_name
        self.scope = scope
        self.session_store = SessionStore(keystore_name)

    def get(self, url, **kwargs):
        """
        Wrapper to make a HTTP GET request with authentication.
        """
        return self._request('GET', url, **kwargs)

    def post(self, url, **kwargs):
        """
        Wrapper to make a HTTP POST request with authentication.
        """
        return self._request('POST', url, **kwargs)

    def put(self, url, **kwargs):
        """
        Wrapper to make a HTTP PUT request with authentication.
        """
        return self._request('PUT', url, **kwargs)

    def delete(self, url, **kwargs):
        """
        Wrapper to make a HTTP DELETE request with authentication.
        """
        return self._request('DELETE', url, **kwargs)

    def _request(self,
                 http_method: str,
                 url: str,
                 perform_auth: bool = True,
                 client_id: str | None = None,
                 client_secret: str | None = None,
                 auth: requests.auth.AuthBase | None = None,
                 **kwargs) -> Response:
        """
        Make an HTTP request with authentication.

        This function looks at the url of the request, determines
        what credentials it should attach to the request to
        authenticate, and then dispatches the request to the
        underlying requests library using the session that
        has been configured with the credentials.

        May prompt the user to perform manual actions (e.g. going to URL to
        enter user code for the device code grant)

        Parameters
        ----------
        http_method : str
            the HTTP verb of the request.
        url : str
            the URL to request
        perform_auth : bool, optional
            Whether to attempt authentication when the initial request is
            rejected with a 401 response. Defaults to ``True``
            as intended by this auth class, however can set to False
            to retrieve and handle the 401 response manually.
        client_id : str, optional
            Client identifier to authenticate with. When given (and ``auth``
            is ``None``) it is used, together with ``client_secret``, as HTTP
            When ``None`` and no credentials are known for the resource, these
            will be obtained using dynamic registration if the resource's
            authorization server supports it.
            See ``authenticate_new_session_from_metadata``.
        client_secret : str, optional
            Client secret matching ``client_id``. May be ``None`` for public
            clients.
        auth : requests.auth.AuthBase, optional
            Authentication handler passed through to ``requests`` as an
            alternative way to pass the client credentials. Will take
            precedence over ``client_id`` and ``client_secret`` if passed alongside
            these parameters.
        **kwargs : Other request kwargs
            Additional kwargs to pass to the request.

        Returns
        -------
        requests.Response
            Response of this request. If authentication was performed
            successfully, this is the response of the retried, authenticated
            request. Otherwise it is the response of the original request.
        """
        session = self.session_store.get_session_for_url(url)

        if auth is None and client_id is not None:
            auth = requests.auth.HTTPBasicAuth(client_id, client_secret)
        response = session.request(http_method, url, auth=auth, **kwargs)

        if response.status_code == 401 and perform_auth:
            # Unauthorized with current auth. Attempt token refresh following RFC9728
            if "WWW-Authenticate" not in response.headers:
                log.debug(
                    "Received 401 from %s but no WWW-Authenticate header was "
                    "provided, unable to discover resource metadata.",
                    url,
                )
                return response

            try:
                rs_metadata_uri = self._parse_resource_metadata_uri(response)
                # Get from either new auth or given auth. Fallback to default
                # if attribute isn't present.
                client_id = getattr(auth, "username", client_id)
                client_secret = getattr(auth, "password", client_secret)
                session, new_secret = self.authenticate_new_session_from_metadata(
                    rs_metadata_uri, client_id, client_secret, url)
            except Exception as e:
                log.debug("Exception during attempted authentication: %s", e)
                return response

            log.debug("Retrying url %s using method %s.", url, http_method)
            new_response = session.request(http_method, url, **kwargs)
            log.debug(
                "Retried request to %s completed with status %s.",
                url,
                new_response.status_code,
            )

            if new_response.ok:
                # The authenticated session worked, keep it for later requests
                # against this resource.
                log.debug(
                    "Storing authenticated session for %s in the session store.",
                    url,
                )
                self.session_store.add_session_for_url(url, session, client_secret=new_secret)
                response = new_response
            else:
                log.debug(
                    "Retried request to %s failed with status %s, "
                    "not storing the session.",
                    url,
                    new_response.status_code,
                )

        return response

    # TODO: This has been copied from a requests-oauthlib fork as detailed at
    #  https://github.com/requests/requests-oauthlib/pull/574.
    #  To not rely on this being merged into requests-oauthlib it has been
    #  added here as a helper function, but should be removed once the above
    #  PR has been merged.
    def token_from_device_code(
        self,
        session,
        device_authorization_endpoint: str,
        token_endpoint: str,
        client_id: str | None = None,
        client_secret: str | None = None,
        interval: float | None = None,
    ) -> dict:
        """
        Prompts request for device code token at ``token_endpoint``. Used
        by DeviceCodeClient. Will continuously loop and poll ``token_endpoint``
        to check the device code until the device code expires or the access
        token is given.

        Parameters
        ----------
        session : ``requests_oauthlib.OAuth2Session``
            The ``OAuth2Session`` used for retrieving the token. Should be
            initialized with the scopes required.
        device_authorization_endpoint : str
            The authorization endpoint used to begin the device code grant.
        token_endpoint : str
            Endpoint for retrieving the token code.
        client_id : str, optional
            Client identifier to be used for token retrieval. When ``None``,
            the client id of ``session`` is used.
        client_secret : str, optional
            The client secret paired with ``client_id``. When ``None``, it is
            omitted from the requests.
        interval : float, optional
            Time in seconds between device code polls. When ``None``, the
            interval returned by the first request is used, defaulting to 5
            seconds as specified by RFC 8628.

        Returns
        -------
        dict
            Token dict as returned by the token endpoint.

        Raises
        ------
        requests.exceptions.HTTPError
            If the device authorization request is rejected.
        TimeoutError
            If the device code expires before the user authorizes the request.
        oauthlib.oauth2.rfc6749.errors.CustomOAuth2Error
            If the token endpoint returns an error other than
            ``authorization_pending`` or ``slow_down``.
        """
        if client_id is None:
            client_id = session.client_id

        auth = requests.auth.HTTPBasicAuth(client_id, client_secret)
        device_code_response = self.post(
            device_authorization_endpoint,
            auth=auth,
            data={"scope": session.scope},
        )
        log.debug(
            "Request device code from %s with client id %s",
            device_authorization_endpoint,
            client_id
        )
        try:
            device_code_response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            log.debug("Failed to authorize:")
            log.debug("Device code response status: %s", device_code_response.status_code)
            log.debug("Device code response content: %s", device_code_response.text)
            raise e

        device_data = device_code_response.json()
        device_code = device_data["device_code"]
        user_code = device_data["user_code"]
        verification_uri = device_data["verification_uri"]
        expires_in = device_data["expires_in"]
        start_time = time.time()
        log.debug("Device code response data: %s", device_data)
        print(f"Go to: {verification_uri}")
        print(f"Enter code: {user_code}")

        token = None
        if interval is None:
            # RFC8628 specifies that clients MUST use 5 as the default
            interval = device_data.get("interval", 5)
        attempts = 0
        while token is None:
            if time.time() - start_time > expires_in:
                raise TimeoutError(
                    "Device code expired"
                )
            attempts += 1
            time.sleep(interval)

            try:
                log.debug("Polling token endpoint %s for device code.", token_endpoint)
                token = session.fetch_token(
                    token_endpoint,
                    device_code=device_code,
                    include_client_id=True,
                    client_id=client_id,
                    client_secret=client_secret,
                    scope=session.scope,
                )
            except CustomOAuth2Error as e:
                if "authorization_pending" in str(e):
                    print(e.description)
                elif "slow_down" in str(e):
                    interval += 5
                    print(f"Polling too fast, trying again in {interval}s")
                else:
                    raise e
        return token

    def authenticate_new_session_from_metadata(
        self,
        rs_metadata_uri: str,
        client_id: str | None = None,
        client_secret: str | None = None,
        redirect_uri: str | None = None,
    ):
        """
        Discover the authorization server for a resource and build an
        authenticated ``requests_oauthlib.OAuth2Session`` for it.

        Parameters
        ----------
        rs_metadata_uri : str
            URL of the protected resource metadata document. Should be found
            as a ``resource_metadata`` property of a
            ``WWW-Authenticate`` header.
        client_id : str, optional
            Client id to authenticate with. If ``None`` along with
            ``client_secret`` being ``None``, a new set of client credentials
            will be retrieved via dynamic registration.
            See ``get_dynamic_client_credentials``.
        client_secret : str, optional
            Client secret matching ``client_id``. May be ``None`` for public
            clients.
        redirect_uri : str, optional
            Redirect URI to associate with the session and with the dynamic
            registration request.

        Returns
        -------
        tuple of (``requests_oauthlib.OAuth2Session``, str or None)
            The authenticated ``requests_oauthlib.OAuth2Session`` and the
            client secret used by it, potentially obtained via the dynamic
            registration flow.

        Raises
        ------
        requests.exceptions.RequestException
            If the resource metadata document could not be retrieved.
        oauthlib.oauth2.ServerError
            If no usable authorization server metadata is found, or if dynamic
            registration is required but not advertised by the authorization
            server.
        oauthlib.oauth2.UnsupportedGrantTypeError
            If no usable grant type could be resolved from the authorization
            server metadata.
        """
        try:
            rs_metadata = self._fetch_json(rs_metadata_uri)
        except requests.exceptions.RequestException as e:
            log.debug("Could not retrieve json from %s (%s).", rs_metadata_uri, e)
            raise e

        # If exception is raised here, let it pass up
        as_metadata = self._discover_as_metadata(rs_metadata)

        scopes = self._resolve_scopes(as_metadata)
        grant_types = self._resolve_grant_types(as_metadata)
        if len(grant_types) == 0:
            raise UnsupportedGrantTypeError("No valid grant types resolved from the "
                                            "authentication server")

        # Register dynamically (RFC 7591) when no credentials are available."""
        log.debug("creds checked: %s %s", client_id, client_secret)
        if client_id is None and client_secret is None:
            log.debug(
                "No client credentials provided, performing dynamic registration."
            )
            if "registration_endpoint" in as_metadata:
                client_id, client_secret = self.get_dynamic_client_credentials(
                    as_metadata["registration_endpoint"], scopes,
                    client_name=self.client_name,
                    grant_types=grant_types,
                    redirect_uri=redirect_uri,
                )
            else:
                raise ServerError("Server does not advertise "
                        "registration_endpoint, unable to perform dynamic "
                        "client registration.")

        session = self._build_session(
            client_id, client_secret, scopes, grant_types,
            as_metadata["token_endpoint"], redirect_uri,
        )

        self._fetch_session_token_based_on_grant_type(
            session, as_metadata, client_id, client_secret
        )
        return session, client_secret

    # Designed as helper classes for authenticate_new_session_from_metadata, but
    # can be used seperately if desired.
    def get_dynamic_client_credentials(
        self,
        registration_endpoint: str,
        scope: Collection[str] | str,
        grant_types: Collection[str] | None = None,
        client_name: str | None = None,
        redirect_uri: str | None = None,
    ) -> tuple[str, str | None]:
        """
        Obtains a new set of client credentials using dynamic registration as
        per RFC7591.

        Parameters
        ----------
        registration_endpoint : str
            Client registration endpoint URL of the authorization server, must
            use HTTPS.
        scope : collection of str or str
            Scopes to request for the new client, either as a space
            separated string or as a collection of scope names. When ``None``,
            the scopes advertised by the authorization server are used.
            See ``_resolve_scopes``.
        grant_types : collection of str, optional
            Grant types the registered client intends to use. When ``None``,
            the grant types stored on construction are used.
            See ``__init__``.
        client_name : str, optional
            Name to register this client under. May be ``None``: will likely
            be treated as anonymous.
        redirect_uri : str, optional
            Redirect URI to attach to the dynamic registration request.

        Returns
        -------
        tuple of (str, str or None)
            The ``client_id`` and ``client_secret`` returned by the
            registration endpoint.

        Raises
        ------
        requests.exceptions.HTTPError
            If the registration request is rejected by the authorization
            server.
        """

        if grant_types is None:
            grant_types = self.grant_types

        if isinstance(scope, Collection) and not isinstance(scope, str):
            scope = " ".join(str(s) for s in scope)

        registration_params = {
            "grant_types": list(grant_types),
            "redirect_uris": [redirect_uri],
            "client_name": client_name,
            "scope": scope,
        }

        registration_response = self.post(
            registration_endpoint,
            json=registration_params
        )
        registration_response.raise_for_status()
        client_metadata = registration_response.json()
        return client_metadata["client_id"], client_metadata.get("client_secret")

    def find_as_metadata(self, authorization_servers: List[str]):
        """
        Locate and retrieve usable authorization server metadata.

        Iterates over the supplied authorization server base URLs and, for each of
        them, checks the two well-known discovery endpoints
        (``/.well-known/openid-configuration`` and
        ``/.well-known/oauth-authorization-server``). Servers whose
        metadata document cannot be fetched, or whose metadata does not advertise a
        ``token_endpoint``, are skipped and the search continues to the next URL.
        The first metadata document that is both reachable and contains a
        ``token_endpoint`` entry is returned.

        Parameters
        ----------
        authorization_servers : List[str]
            Base URLs of the authorization servers to probe, tried in the given
            order.

        Returns
        -------
        dict
            Parsed authorization server metadata document that advertises a
            ``token_endpoint``.

        Raises
        ------
        ServerError
            If none of the supplied authorization servers exposes reachable
            metadata containing a ``token_endpoint``.
        """
        for as_base in authorization_servers:  # Try each authorization server
            for as_metadata_uri in [f"{as_base}/.well-known/openid-configuration",
                                        f"{as_base}/.well-known/oauth-authorization-server"]:
                log.debug(
                    "Fetching authorization server metadata from %s", as_metadata_uri
                )
                try:
                    as_metadata = self._fetch_json(as_metadata_uri)
                except requests.exceptions.RequestException as e:
                    log.debug(
                        "No accessible authorization metadata at %s, error: %s",
                        as_metadata_uri, e
                    )
                    continue

                if "token_endpoint" not in as_metadata:
                    log.debug(
                        "Authorization server metadata at %s does not advertise "
                        "a token_endpoint, "
                        "trying next authorization server.",
                        as_metadata_uri,
                    )
                    continue
                else:
                    return as_metadata
        # No usable as_metadata found
        raise ServerError("No usable authorization server metadata found"
                          f"in {authorization_servers}")

    # Private helpers for authenticate_new_session_from_metadata
    def _fetch_session_token_based_on_grant_type(self,
                                                 session: OAuth2Session,
                                                 as_metadata: dict,
                                                 client_id: str,
                                                 client_secret: str):
        """
        Follow the token retrieval method appropriate for the client type,
        using the given client ID and secret.

        Required as requests-oauthlib sometimes uses different functions
        on its OAuth2Session to retrieve tokens (most specifically
        token_from_fragment).
        """
        token_endpoint = as_metadata["token_endpoint"]

        if isinstance(session._client, DeviceClient):
            if "device_authorization_endpoint" in as_metadata:
                authorization_url, _state = session.authorization_url(
                    as_metadata["device_authorization_endpoint"]
                )
            else:
                # No specific authorization endpoint published
                # Leaning back on the regular authorization endpoint
                authorization_url, _state = session.authorization_url(
                    as_metadata["authorization_endpoint"]
                )

            log.debug("Device flow detected, polling %s for a token.",
                      authorization_url)
            self.token_from_device_code(
                session,
                authorization_url,
                token_endpoint,
                client_id=client_id,
                client_secret=client_secret,
            )
        else:
            session.fetch_token(
                token_endpoint,
                auth=(client_id, client_secret),
                include_client_id=True
            )

    @staticmethod
    def _fetch_json(url: str):
        """Retrieve json via GET request from a given URL

        Metadata documents must be readable by unauthenticated clients, so a
        plain ``requests`` call is used here.

        Any exceptions that are raised during raise_for_status or response.json
        should be raised by the caller as well.
        """
        log.debug("Fetching json from %s", url)
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

    def _discover_as_metadata(self, rs_metadata: dict) -> dict:
        """Resolve usable authorization server metadata from resource metadata."""
        log.debug("Resource metadata: %s", rs_metadata)

        as_servers: List[str] | None = rs_metadata.get("authorization_servers")
        if not as_servers:
            raise ServerError("No authorization servers advertised in resource server metadata")

        as_metadata = self.find_as_metadata(as_servers)
        return as_metadata

    @staticmethod
    def _parse_resource_metadata_uri(response: Response):
        """Extract the ``resource_metadata`` property from a 401 challenge header
        from the given response object"""
        www_auth_headers = response.headers.get("WWW-Authenticate").split(",")

        for scheme in www_auth_headers:
            # Properties split by spaces
            for prop in scheme.split(" "):
                if prop.startswith("resource_metadata="):
                    # Extract the prop value from resource_metadata=resource_metadata_url
                    return prop.split("=")[1]

        raise OAuth2Error("No resource metadata URI found in WWW-Authenticate header")

    def _resolve_scopes(self, as_metadata) -> set | None:
        """Use the configured scopes, falling back to those the server advertises."""
        as_metadata_scopes = as_metadata.get("scopes_supported")
        if self.scope is None and as_metadata_scopes:
            return set(as_metadata["scopes_supported"])
        return self.scope

    def _resolve_grant_types(self, as_metadata: dict) -> List[str]:
        """Intersect the configured grant types with the advertised ones.

        Returns empty list when the authorization server does not advertise any
        grant types or if no requested grant types are supported. Will end up
        attempting to use the default client.
        """
        advertised = as_metadata.get("grant_types_supported")
        if advertised is None:
            return []

        advertised = set(advertised)
        if self.grant_types is None:
            usable = advertised
        else:
            usable = set(self.grant_types) & advertised

        log.debug(
            "Authorization server advertises grant types %s, client is "
            "configured for %s, possible session grant types: %s.",
            advertised, self.grant_types, usable,
        )
        return usable

    @staticmethod
    def _select_client_class(grant_types):
        """Return ``(grant_type, client_class)`` for the first supported grant."""
        for grant_type in grant_types:
            client_class = GRANT_TO_CLIENT_CLASS.get(grant_type)
            if client_class is not None:
                return grant_type, client_class
        return None, None

    def _build_session(self,
                       client_id: str,
                       client_secret: str,
                       scopes: str,
                       grant_types: List[str],
                       token_endpoint: str,
                       redirect_uri: str):
        """Create the ``requests_oauthlib.OAuth2Session`` matching the negotiated grant type."""
        session_kwargs = {
            'scope': scopes,
            'redirect_uri': redirect_uri,
            'auto_refresh_url': token_endpoint,
            'auto_refresh_kwargs': {
                'client_id': client_id,
                'client_secret': client_secret,
            },
        }

        if not grant_types:
            # Nothing advertised (or nothing in common): use the default client.
            return OAuth2Session(client_id=client_id, **session_kwargs)

        grant_type, client_class = self._select_client_class(grant_types)
        if client_class is None:
            raise UnsupportedGrantTypeError(
                "No usable grant type available from authorization server "
                f"(candidates were {grant_types})."
            )

        log.debug(
            "Using grant type %s with client class %s.",
            grant_type,
            client_class.__name__,
        )
        return OAuth2Session(client=client_class(client_id=client_id), **session_kwargs)
