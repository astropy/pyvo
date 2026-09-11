import logging
from typing import Collection, List

import requests
from oauthlib.oauth2 import DeviceClient
from requests_oauthlib import OAuth2Session

from .sessionstore import SessionStore

__all__ = ["PyvoOAuth2Session"]

# Service name used to namespace entries in the system keystore.
DEFAULT_KEYSTORE_SERVICE_NAME = 'pyvo.auth.oauth2'

# Module level logger used to report authentication diagnostics.
log = logging.getLogger(__name__)

GRANT_TO_CLIENT_CLASS = {
    # 'authorization_code': WebApplicationClient,
    # 'implicit': MobileApplicationClient,
    # 'urn:ietf:params:oauth:grant-type:jwt-bearer' : ServiceApplicationClient,
    # 'client_credentials': BackendApplicationClient,
    'urn:ietf:params:oauth:grant-type:device_code': DeviceClient,
}

class PyvoOAuth2Session:
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

    def _request(self, http_method, url, perform_auth=True, client_id=None, client_secret=None, **kwargs):
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
        response = session.request(http_method, url, **kwargs)

        if response.status_code == 401 and perform_auth:
            # Unauthorized with current auth. Attempt token refresh following RFC9728
            if "WWW-Authenticate" not in response.headers:
                log.debug(
                    "Received 401 from %s but no WWW-Authenticate header was "
                    "provided, unable to discover resource metadata.",
                    url,
                )
                return response
            rs_metadata_uri = self._parse_resource_metadata_uri(response)
            if rs_metadata_uri is None:
                log.debug(
                    "No resource_metadata advertised in the WWW-Authenticate "
                    "header of the 401 response from %s.",
                    url,
                )
                return response

            session = self.authenticate_new_session_from_metadata(rs_metadata_uri, client_id, client_secret, url)
            if session is None: # New session didn't authenticate properly
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
                self.session_store.add_session_for_url(url, session, client_secret=client_secret)
                response = new_response
            else:
                log.debug(
                    "Retried request to %s failed with status %s, "
                    "not storing the session.",
                    url,
                    new_response.status_code,
                )

        return response

    def authenticate_new_session_from_metadata(self, rs_metadata_uri, client_id,
                                               client_secret, redirect_uri=None):
        """
        Discover the authorization server for a resource and build an
        authenticated :class:`~requests_oauthlib.OAuth2Session` for it.

        Returns ``None`` if discovery or the token exchange fails.
        """
        rs_metadata = self._fetch_json(rs_metadata_uri)
        if rs_metadata is None:
            return None

        as_metadata = self._discover_as_metadata(rs_metadata)
        if as_metadata is None:
            return None

        scopes = self._resolve_scopes(as_metadata)
        grant_types = self._resolve_grant_types(as_metadata)

        # Register dynamically (RFC 7591) when no credentials are available."""
        if client_id is None and client_secret is None:
            log.debug(
                "No client credentials provided, performing dynamic registration"
            )
            if "registration_endpoint" in as_metadata:
                client_id, client_secret = self.get_dynamic_client_credentials(
                    as_metadata["registration_endpoint"], scopes,
                    client_name=self.client_name,
                    grant_types=grant_types,
                    redirect_uri=redirect_uri,
                )
            else:
                log.debug(
                    "Server does not advertise a registration_endpoint, unable "
                    "to perform dynamic client registration (RFC 7591)."
                )
                return None

        token_endpoint = as_metadata["token_endpoint"]

        session = self._build_session(
            client_id, client_secret, scopes, grant_types,
            token_endpoint, redirect_uri,
        )
        if session is None:
            return None

        self._fetch_session_token_based_on_grant_type(session, token_endpoint, client_id, client_secret)
        return session

    # -- discovery helpers -------------------------------------------------
    @staticmethod
    def _fetch_session_token_based_on_grant_type(session, auth_endpoint, client_id, client_secret):
        # Perform authentication based on client type
        authorization_url, _state = session.authorization_url(auth_endpoint)

        if isinstance(session._client, DeviceClient):
            log.debug("Device flow detected, polling %s for a token.",
                      authorization_url)
            session.token_from_device_code(
                authorization_url,
                client_id=client_id,
                client_secret=client_secret,
            )
        # elif isinstance(session._client, MobileApplicationClient):
        #     log.debug("Implicit flow detected, requesting authorization at %s.",
        #               authorization_url)
        #     print(f"Go to: {authorization_url}")
        #     authorization_response = input(
        #         "Paste the full redirect URL you were sent to here: "
        #     )
        #     session.token_from_fragment(authorization_response)
        else:
            session.refresh_token(
                authorization_url,
                auth=(client_id, client_secret),
            )


    @staticmethod
    def _fetch_json(url):
        """GET ``url`` and decode it as JSON, returning ``None`` on any failure.

        Metadata documents must be readable by unauthenticated clients, so a
        plain `requests` call is used here.
        """
        log.debug("Fetching json from %s",  url)
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            log.debug("Could not retrieve json from %s (%s).",  url, e)
        except ValueError as e:
            # Includes json.JSONDecodeError for non-JSON/malformed bodies
            log.debug("Invalid JSON (%s).", e)
        return None

    def _discover_as_metadata(self, rs_metadata) -> dict:
        """Resolve usable authorization server metadata from resource metadata."""
        log.debug("Resource metadata: %s", rs_metadata)

        as_servers = rs_metadata.get("authorization_servers")
        if not as_servers:
            log.debug(
                "No authorization servers advertised in resource server metadata,"
                " skipping token retrieval."
            )
            return None

        as_metadata = self._find_as_metadata(as_servers)
        if as_metadata is None:
            log.debug(
                "None of the advertised authorization servers %s provided usable "
                "metadata.",
                as_servers,
            )
        return as_metadata

    # -- session configuration helpers ------------------------------------

    def _resolve_scopes(self, as_metadata) -> set | None:
        """Use the configured scopes, falling back to those the server advertises."""
        if self.scope is None and "scopes_supported" in as_metadata:
            return set(as_metadata["scopes_supported"])
        return self.scope

    def _resolve_grant_types(self, as_metadata) -> List[str] | None:
        """Intersect the configured grant types with the advertised ones.

        Returns ``None`` when the authorization server does not advertise any
        grant types, meaning the default client should be used.
        """
        advertised = as_metadata.get("grant_types_supported")
        if advertised is None:
            return None

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
            log.debug(
                "No usable grant type available from authorization server "
                "(candidates were %s).",
                sorted(grant_types),
            )
            return None

        log.debug(
            "Using grant type %s with client class %s.",
            grant_type,
            client_class.__name__,
        )
        return OAuth2Session(client=client_class(client_id=client_id), **session_kwargs)

    # -- token retrieval ---------------------------------------------------
    def get_dynamic_client_credentials(self, registration_endpoint, scope, grant_types=None, client_name=None, redirect_uri=None):
        """
        Obtains a new set of client credentials using dynamic registration as per RFC7591.

        :param registration_endpoint: Client registration endpoint URL of the
                                      authorization server, must use HTTPS.
        :param grant_types: Optional list of grant types the registered client
                            intends to use. Defaults to an empty list, to which
                            the grant type of the underlying client is appended
                            when available.
        :param client_name: Optional human readable name of this client, sent to
                            the registration endpoint so the authorization
                            server can identify and display the registered
                            client. May be None, in which case the client is
                            likely to be treated as anonymous.
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

        registration_response = self.post(registration_endpoint, json=registration_params
        )
        registration_response.raise_for_status()
        client_metadata = registration_response.json()
        return client_metadata["client_id"], client_metadata.get("client_secret")

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

        return None  # No resource metadata URI found

    def _find_as_metadata(self, authorization_servers):
        for as_base in authorization_servers:  # Try each authorization server
            for as_metadata_uri in [f"{as_base}/.well-known/openid-configuration",
                                        f"{as_base}/.well-known/oauth-authorization-server"]:
                log.debug(
                    "Fetching authorization server metadata from %s", as_metadata_uri
                )
                as_metadata = self._fetch_json(as_metadata_uri)

                if as_metadata is None:
                    log.debug(
                        "No accessible authorization metadata at %s",
                        as_metadata_uri,
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
        return None
