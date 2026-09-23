import logging
from typing import Collection, List

import requests
from oauthlib.oauth2 import DeviceClient, ServerError, UnsupportedGrantTypeError, OAuth2Error
from requests_oauthlib import OAuth2Session

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
        grant_types=None,
        client_name=None,
        scope=None,
        keystore_name=DEFAULT_KEYSTORE_SERVICE_NAME
    ):
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

    def _request(self, http_method, url, perform_auth=True, client_id=None,
                 client_secret=None, auth=None, **kwargs):
        """
        Make an HTTP request with authentication.

        This function looks at the url of the request, determines
        what credentials it should attach to the request to
        authenticate, and then dispatches the request to the
        underlying requests library using the session that
        has been configured with the credentials.

        Parameters
        ----------
        http_method : str
            the HTTP verb of the request.
        url : str
            the URL to request
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

    def authenticate_new_session_from_metadata(self,
                                               rs_metadata_uri,
                                               client_id=None,
                                               client_secret=None,
                                               redirect_uri=None):
        """
        Discover the authorization server for a resource and build an
        authenticated :class:`requests_oauthlib.OAuth2Session` for it.

        Returns ``None`` if discovery or the token exchange fails.

        :param rs_metadata_uri: URL of the protected resource metadata document.
                                Should be found under the ``resource_metadata``
                                parameter of a ``WWW-Authenticate`` header.
        :param client_id: Optional client identifier to authenticate with.
                          If given will attempt to retrieve a token with these
                          credentials. If not along with `client_secret`
                          then the dynamic registration flow will occur
        :param client_secret: Optional client secret matching `client_id`. May be
                              None for public clients.
        :param redirect_uri: Redirect URI to associate with the session and with
                             the dynamic registration request. Most likely the
                             protected resource you are getting a token for.
        :return: A tuple of the authenticated
                 :class:`requests_oauthlib.OAuth2Session` and the client secret
                 used by it, potentially obtained via the dynamic registration
                 flow. Or tuple of None, None if the flow fails at any point.
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

        self._fetch_session_token_based_on_grant_type(session, as_metadata, client_id, client_secret)
        return session, client_secret

    # Designed as helper classes for authenticate_new_session_from_metadata, but
    # can be used seperately if desired.
    def get_dynamic_client_credentials(self, registration_endpoint, scope, grant_types=None, client_name=None, redirect_uri=None):
        """
        Obtains a new set of client credentials using dynamic registration as per RFC7591.

        :param registration_endpoint: Client registration endpoint URL of the
                                      authorization server, must use HTTPS.
        :param scope: List of scopes either as a space seperated string or
                      collection that can be joined into a space seperated
                      string.
        :param grant_types: Optional list of grant types the registered client
                            intends to use. Defaults to an empty list, to which
                            the grant type stored on construction is used.
        :param client_name: Optional human readable name of this client, sent to
                            the registration endpoint so the authorization
                            server can identify and display the registered
                            client. May be None: most systems will treat
                            this as anonymous.
        :param redirect_uri: Redirect URI to attach to the dynamic registration
                             request.
        :return: The client_id and client_secret returned by the registration endpoint.
                The issued `client_id` is stored on this session.
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

    def find_as_metadata(self, authorization_servers):
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
    @staticmethod
    def _fetch_session_token_based_on_grant_type(session, as_metadata, client_id, client_secret):
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
            session.token_from_device_code(
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
    def _fetch_json(url):
        """Retrieve json via `GET` request from a given URL

        Metadata documents must be readable by unauthenticated clients, so a
        plain `requests` call is used here.

        Any exceptions that are raised during raise_for_status or response.json
        should be raised by the caller as well.
        """
        log.debug("Fetching json from %s", url)
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

    def _discover_as_metadata(self, rs_metadata) -> dict:
        """Resolve usable authorization server metadata from resource metadata."""
        log.debug("Resource metadata: %s", rs_metadata)

        as_servers = rs_metadata.get("authorization_servers")
        if not as_servers:
            raise ServerError("No authorization servers advertised in resource server metadata")

        as_metadata = self.find_as_metadata(as_servers)
        return as_metadata

    @staticmethod
    def _parse_resource_metadata_uri(response):
        """Extract the `resource_metadata` uri from a 401 challenge header."""
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

    def _resolve_grant_types(self, as_metadata) -> List[str]:
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

    def _build_session(self, client_id, client_secret, scopes, grant_types,
                       token_endpoint, redirect_uri):
        """Create the :class:`OAuth2Session` matching the negotiated grant type."""
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
