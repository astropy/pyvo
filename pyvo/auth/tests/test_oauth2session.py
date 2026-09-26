"""
Tests for pyvo.auth.oauth2.oauth2session (PyvoOAuth2Session) to ensure
correct authentication flow and handling of potential failure conditions.
"""
import base64
from contextlib import ExitStack
from urllib.parse import parse_qs
import pytest

pytest.importorskip("keyring", reason="oauth2 extra (keyring) not installed")
pytest.importorskip(
    "requests_oauthlib", reason="oauth2 extra (requests-oauthlib) not installed"
)

from oauthlib.oauth2 import ServerError, UnsupportedGrantTypeError
from requests.exceptions import HTTPError
from pyvo.auth.oauth2.oauth2session import VOAuthSession

@pytest.fixture()
def setup_test_server(mocker):
    """
    Pytest fixture to setup a mock server to test authentication flow. It
    provides a function that is to be initialized at the start of a test.
    Provides all endpoints for the authentication flow upon 401 response

    Some of the metadata and token values can be changed from their defaults set
    in the function paraemters. Changes from their defaults will invalidate the
    flow. It however allows us to test invalid metadata and the handling of
    such.

    Will return a list of matchers for each endpoint,which can be checked for
    call counts
    """
    with ExitStack() as stack:
        def _setup_test_server(
            www_authenticate=(
                'Bearer realm="test", resource_metadata='
                'https://example.com/tap/.well-known/oauth-protected-resource'
            ),
            
            correct_token="correcttoken",
            authorization_servers_list={"https://as-server1.com"},
            as_server_scopes=None,
            as_grant_types={
                "urn:ietf:params:oauth:grant-type:device_code",
                "refresh_token"
            },
            registered_client_id="test-client-id",
            registered_client_secret="test-client-secret",
        ):
            def check_client_credentials(request_authorization_token):
                valid_client_credentials = [
                    base64.b64encode(
                        f"{cid}:{csecret}".encode()
                    ).decode() for cid, csecret in
                    [
                        (registered_client_id, registered_client_secret),
                        ("explicit-client-id", "explicit-client-secret")
                    ]
                ]
                return request_authorization_token in valid_client_credentials


            def resource_callback(request, context):
                # Check for bearer token and its validity
                authorization = request.headers.get("Authorization", "")
                if not authorization.startswith("Bearer "):
                    context.status_code = 401
                    if www_authenticate is not None:
                        context.headers["WWW-Authenticate"] = www_authenticate
                    return "unauthorized"

                request_token = authorization.split(" ")[1]
                if request_token != correct_token:
                    context.status_code = 401
                    if www_authenticate is not None:
                        context.headers["WWW-Authenticate"] = www_authenticate
                    return "unauthorized"

                context.status_code = 200
                return "secret data"
            
            def device_authorization_callback(request, context):
                request_auth = request.headers.get("Authorization")

                if request_auth is not None and check_client_credentials(request_auth.split(" ")[1]):
                    context.status_code = 200
                    return {
                        "device_code": "test-device-code",
                        "user_code": "TEST-USER-CODE",
                        "verification_uri": "https://as-server1.com/device",
                        "verification_uri_complete":
                            "https://as-server1.com/device?user_code=TEST-USER-CODE",
                        "expires_in": 1800,
                        "interval": 0,
                    }

                context.status_code = 401
                return {
                    "error": "invalid_client",
                    "error_description":
                        "invalid client credentials",
                }


            def token_callback(request, context):
                request_body_qs =  parse_qs(request.text)
                grant_type = request_body_qs.get("grant_type", [None])[0]
                if grant_type == "urn:ietf:params:oauth:grant-type:device_code":
                    device_code = request_body_qs.get("device_code", [None])[0]
                    print("device code:", device_code)
                    if device_code == "test-device-code":
                        context.status_code = 200
                        return {
                            "access_token": correct_token,
                            "token_type": "Bearer",
                            "expires_in": 3600,
                        }
                    else:
                        context.status_code = 400
                        return {
                            "error": "invalid_grant",
                            "error_description":
                                "invalid or expired device code",
                        }

                context.status_code = 400
                return {
                    "error": "invalid_grant",
                    "error_description":
                        f"unknown grant type {grant_type}",
                }

            # Build matchers dynamically depending on options
            return [
                # resource server
                stack.enter_context(
                    mocker.register_uri(
                        "GET", "https://example.com/tap",
                        text=resource_callback
                    )
                ),
                stack.enter_context(
                    mocker.register_uri(
                        "GET", "https://example.com/tap/.well-known/oauth-protected-resource",
                        json={
                            "resource": "https://example.com/tap",
                            "authorization_servers": list(authorization_servers_list)
                            if authorization_servers_list is not None else None
                        }
                    )
                ),
                # Just as-server1
                stack.enter_context(
                    mocker.register_uri(
                        "GET", "https://as-server1.com/.well-known/openid-configuration",
                        status_code=404
                    )
                ),
                stack.enter_context(
                    # Already separate tests for find_as_metadata, just provide
                    # a working metadata document
                    mocker.register_uri(
                        "GET", "https://as-server1.com/.well-known/oauth-authorization-server",
                        json={
                            "issuer": "https://as-server1.com",
                            "token_endpoint": "https://as-server1.com/token",
                            "registration_endpoint": "https://as-server1.com/register",
                            "device_authorization_endpoint": "https://as-server1.com/device_authorization",
                            "grant_types_supported": list(as_grant_types)
                            if as_grant_types is not None else None,
                            "scopes_supported": list(as_server_scopes)
                            if as_server_scopes is not None else None
                        }
                    )
                ),
                stack.enter_context(
                    mocker.register_uri(
                        "POST", "https://as-server1.com/register",
                        json={
                            "client_id": registered_client_id,
                            "client_secret": registered_client_secret,
                            "grant_types": list(as_grant_types)
                            if as_grant_types is not None else None,
                            "scope": " ".join(as_server_scopes)
                            if as_server_scopes else None
                        },
                        status_code=201
                    )
                ),
                stack.enter_context(
                    mocker.register_uri(
                        "POST", "https://as-server1.com/device_authorization",
                        json=device_authorization_callback
                    )
                ),
                stack.enter_context(
                    mocker.register_uri(
                        "POST", "https://as-server1.com/token",
                        json=token_callback
                    )
                ),
            ]

        yield _setup_test_server

def test_as_server_retrieval_openid_configuration(mocker):
    with mocker.register_uri(
        "GET", "https://as-server1/cas/.well-known/openid-configuration",
        json={
            "issuer": "https://as-server1/cas",
            # Missing token endpoint
        }
    ), mocker.register_uri(
        "GET", "https://as-server1/cas/.well-known/oauth-authorization-server",
        status_code=404
    ), mocker.register_uri(
        "GET", "https://as-server2/cas/.well-known/openid-configuration",
        json={
            "issuer": "https://as-server2/cas",
            "token_endpoint": "https://abitrary-endpoint.com/token",
        }
    ), mocker.register_uri(
        "GET", "https://as-server2/cas/.well-known/oauth-authorization-server",
        status_code=404
    ):
        session = VOAuthSession()
        metadata = session.find_as_metadata(
            ["https://as-server1/cas", "https://as-server2/cas"])

    assert metadata is not None
    assert metadata["issuer"] == "https://as-server2/cas"
    assert metadata["token_endpoint"] == "https://abitrary-endpoint.com/token"

def test_as_server_retrieval_oauth_authorization_server(mocker):
    with mocker.register_uri(
        "GET", "https://as-server1/cas/.well-known/oauth-authorization-server",
        json={
            "issuer": "https://as-server1/cas",
            # Missing token endpoint
        }
    ), mocker.register_uri(
        "GET", "https://as-server1/cas/.well-known/openid-configuration",
        status_code=404
    ), mocker.register_uri(
        "GET", "https://as-server2/cas/.well-known/oauth-authorization-server",
        status_code=500, text="internal server error",
    ), mocker.register_uri(
        "GET", "https://as-server2/cas/.well-known/openid-configuration",
        status_code=404
    ), mocker.register_uri(
        "GET", "https://as-server3/cas/.well-known/openid-configuration",
        status_code=404
    ), mocker.register_uri(
        "GET", "https://as-server3/cas/.well-known/oauth-authorization-server",
        json={
            "issuer": "https://as-server3/cas",
            "token_endpoint": "https://abitrary-endpoint.com/token",
        }
    ):
        session = VOAuthSession()
        metadata = session.find_as_metadata([
            "https://as-server1/cas",
            "https://as-server2/cas",
            "https://as-server3/cas",
        ])

    assert metadata is not None
    assert metadata["issuer"] == "https://as-server3/cas"
    assert metadata["token_endpoint"] == "https://abitrary-endpoint.com/token"


def test_as_server_discovery_no_as_urls_in_rs_metadata():
    session = VOAuthSession()
    with pytest.raises(ServerError):
        session._discover_as_metadata(
            {"error": "Missing advertisable authorization servers"}
        )

def test_rs_metadata_failure_raises(mocker):
    session = VOAuthSession()
    with mocker.register_uri("GET", "https://as-server1/bad-rs-metadata", status_code=404):
        with pytest.raises(HTTPError) as e:
            session.authenticate_new_session_from_metadata(
                "https://as-server1/bad-rs-metadata"
            )

            assert e.value.response.status_code == 404

def test_no_grant_type_match(mocker):
    session = VOAuthSession(grant_types=["something_different"])
    with mocker.register_uri("GET", "https://example.com/rs-metadata",
            json={"authorization_servers": ["https://as-server1/cas"]}
    ), mocker.register_uri(
        "GET", "https://as-server1/cas/.well-known/openid-configuration",
        json={
            "token_endpoint": "https://as-server1.com/token",
            "grant_types_supported": ["nothing_familiar"]
        }
    ):
        with pytest.raises(UnsupportedGrantTypeError):
            session.authenticate_new_session_from_metadata(
                "https://example.com/rs-metadata"
            )


def test_no_compatible_authorization_servers(fake_keyring, mocker):
    with mocker.register_uri(
        "GET", "https://as-server1/cas/.well-known/oauth-authorization-server",
        json={
            "issuer": "https://as-server1/cas",
            # Missing token endpoint
        }
    ), mocker.register_uri(
        "GET", "https://as-server1/cas/.well-known/openid-configuration",
        status_code=404, text="not found",
    ), mocker.register_uri(
        "GET", "https://as-server2/cas/.well-known/openid-configuration",
        status_code=404, text="not found",
    ), mocker.register_uri(
        "GET", "https://as-server2/cas/.well-known/oauth-authorization-server",
        status_code=404, text="not found",
    ), mocker.register_uri(
        "GET", "https://as-server3/cas/.well-known/openid-configuration",
        status_code=404, text="not found",
    ), mocker.register_uri(
        "GET", "https://as-server3/cas/.well-known/oauth-authorization-server",
        status_code=404, text="not found",
    ):
        session = VOAuthSession()
        with pytest.raises(ServerError):
            session.find_as_metadata([
                "https://as-server1/cas",
                "https://as-server2/cas",
                "https://as-server3/cas",
            ])

def test_scope_resolution_session_from_construction():
    """
    Ensure scopes provided to session are prioritized over the authorization
    server metadata
    """
    session = VOAuthSession(
        scope=["read", "write"],
    )
    # Used regardless of as_metadata
    scopes = session._resolve_scopes(
        {"scopes_supported": ["openid", "profile"]})
    assert scopes is not None
    assert set(scopes) == {"read", "write"}

    # Also used with empty scope metadata
    scopes = session._resolve_scopes({})
    assert scopes is not None
    assert set(scopes) == {"read", "write"}

def test_scope_resolution_session_from_metadata():
    session = VOAuthSession()
    scopes = session._resolve_scopes(
        {"scopes_supported": ["openid", "profile", "offline_access"]})
    assert scopes is not None
    assert set(scopes) == {"openid", "profile", "offline_access"}
    assert not session._resolve_scopes({"scopes_supported": []})

def test_scope_empty_metadata():
    session = VOAuthSession()
    scopes = session._resolve_scopes({})
    assert scopes is None


def test_grant_types_resolution_no_metadata():
    session = VOAuthSession()
    # Defaults to None if not stored on construction with empty metadata
    assert len(session._resolve_grant_types({})) == 0

    session = VOAuthSession(
        grant_types=["refresh_token"],
    )
    # Still needs to intersect with metadata, will be empty
    assert len(session._resolve_grant_types({})) == 0


def test_grant_types_resolution_from_metadata():
    session = VOAuthSession()
    grant_types = session._resolve_grant_types({
        "grant_types_supported": [
            "urn:ietf:params:oauth:grant-type:device_code",
            "refresh_token",
        ]
    })
    assert set(grant_types) == {
        "urn:ietf:params:oauth:grant-type:device_code",
        "refresh_token",
    }

    # Intersects with none
    assert len(session._resolve_grant_types({"grant_types_supported": []})) == 0


def test_grant_types_resolution_intersection():
    session = VOAuthSession(
        grant_types=[
            "urn:ietf:params:oauth:grant-type:device_code",
            "authorization_code",
        ],
    )
    grant_types = session._resolve_grant_types({
        "grant_types_supported": [
            "urn:ietf:params:oauth:grant-type:device_code",
            "refresh_token",
        ]
    })
    assert set(grant_types) == {
        "urn:ietf:params:oauth:grant-type:device_code"
    }


def test_grant_types_resolution_no_overlap():
    """No common grant type means no usable grant type at all."""
    session = VOAuthSession(
        grant_types=["authorization_code"],
    )
    grant_types = session._resolve_grant_types({
        "grant_types_supported": [
            "urn:ietf:params:oauth:grant-type:device_code",
            "refresh_token",
        ]
    })
    assert len(grant_types) == 0


def test_grant_types_resolution_empty_client_configuration():
    """An explicitly empty client configuration disables every grant type."""
    session = VOAuthSession(
        grant_types=[],
    )
    grant_types = session._resolve_grant_types({
        "grant_types_supported": ["refresh_token"]
    })
    assert grant_types is not None
    assert not grant_types


def test_401_without_www_authenticate_just_returns(mocker):
    """A 401 that carries no ``WWW-Authenticate`` header cannot trigger
    RFC9728 discovery, so the original response must be returned as-is."""
    session = VOAuthSession()

    with mocker.register_uri(
        "GET", "https://example.com/tap",
        status_code=401, text="unauthorized",
    ) as matcher:
        response = session.get("https://example.com/tap")
        assert matcher.called_once

    assert response.status_code == 401
    assert response.text == "unauthorized"

    # No re-authentication happened, so nothing was cached for the URL.
    with pytest.raises(KeyError):
        session.session_store["https://example.com/tap"]

def test_401_missing_resource_metadata_just_returns(mocker):
    # Can"t perform authentication if theres no metadata to work off
    session = VOAuthSession()
    with mocker.register_uri(
        "GET", "https://rs.example.com/no-resource-metadata/tap",
        status_code=401, text="unauthorized",
        headers={"WWW-Authenticate": 'Bearer realm="example"'},
    ) as matcher:
        response = session.get("https://rs.example.com/no-resource-metadata/tap")
        assert matcher.called_once

    assert response.status_code == 401
    assert response.text == "unauthorized"

    # Failed authentication fails to store session
    with pytest.raises(KeyError):
        session.session_store["https://rs.example.com/no-resource-metadata/tap"]


def test_dynamic_registration_gets_token(mocker, setup_test_server):
    matchers = setup_test_server()

    (_resource_matcher, rs_metadata_matcher, _openid_matcher,
     as_metadata_matcher, register_matcher, authorization_matcher,
     token_matcher) = matchers

    session = VOAuthSession()

    oauthlib_session, new_client_secret = session.authenticate_new_session_from_metadata(
        "https://example.com/tap/.well-known/oauth-protected-resource",
    )
    session.session_store.add_session_for_url("https://example.com/tap", oauthlib_session)

    # Discovery endpoints called
    assert rs_metadata_matcher.called_once
    assert as_metadata_matcher.called_once
    assert register_matcher.called_once
    assert authorization_matcher.called_once
    assert token_matcher.called_once

    # Attributes we gave are the same
    assert session.session_store["https://example.com/tap"].client_id == "test-client-id"
    assert session.session_store["https://example.com/tap"].token["access_token"] == "correcttoken"
    assert new_client_secret == "test-client-secret"

def test_dynamic_registration_skipped_with_explicit_client_id_secret(mocker, setup_test_server):
    matchers = setup_test_server()

    (_resource_matcher, rs_metadata_matcher, _openid_matcher,
     as_metadata_matcher, register_matcher, authorization_matcher,
     token_matcher) = matchers
    
    session = VOAuthSession()

    oauthlib_session, new_client_secret = session.authenticate_new_session_from_metadata(
        "https://example.com/tap/.well-known/oauth-protected-resource",
        client_id="explicit-client-id",
        client_secret="explicit-client-secret",
    )

    # Discovery endpoints called
    assert rs_metadata_matcher.called_once
    assert as_metadata_matcher.called_once
    assert token_matcher.called_once
    assert authorization_matcher.called_once
    # Dynamic registration skipped
    print("register matcher:", register_matcher)
    assert register_matcher.call_count == 0

    # Attributes we gave are the same
    assert oauthlib_session.client_id == "explicit-client-id"
    assert oauthlib_session.token["access_token"] == "correcttoken"
    assert new_client_secret == "explicit-client-secret" # remains the same


def test_authentication_flow(setup_test_server):
    # Follow the full authentication flow on 401 and ensure all steps are executed
    session = VOAuthSession()

    matchers = setup_test_server(
        registered_client_id="new-client",
        registered_client_secret="new-secret",
    )

    (resource_matcher, rs_metadata_matcher, _openid_matcher,
     as_metadata_matcher, register_matcher, authorization_matcher,  token_matcher) = matchers
    response = session.get("https://example.com/tap")

    # Ensure the final contact is successful
    assert response.status_code == 200
    assert response.text == "secret data"

    # Called on 401 and after authentication
    assert resource_matcher.call_count == 2
    # All auth endpoints have been contacted once for auth flow
    assert rs_metadata_matcher.called_once
    assert as_metadata_matcher.called_once
    assert register_matcher.called_once
    assert authorization_matcher.called_once
    assert token_matcher.called_once

    # Ensure client details and token are cached
    stored_session = session.session_store["https://example.com/tap"]
    assert stored_session.client_id == "new-client"
    assert stored_session.token["access_token"] == "correcttoken"
    assert (session.session_store.get_client_secret_for_url(
        "https://example.com/tap") == "new-secret")

    response = session.get("https://example.com/tap")

    assert response.status_code == 200
    assert response.text == "secret data"

    # Resource contacted once more
    assert resource_matcher.call_count == 3
    # With the token, should not have touched any of the auth endpoints
    assert rs_metadata_matcher.called_once
    assert as_metadata_matcher.called_once
    assert register_matcher.called_once
    assert authorization_matcher.called_once
    assert token_matcher.called_once

    # The cached credentials are left untouched.
    stored_session = session.session_store["https://example.com/tap"]
    assert stored_session.client_id == "new-client"
    assert stored_session.token["access_token"] == "correcttoken"
    assert (session.session_store.get_client_secret_for_url(
        "https://example.com/tap") == "new-secret")

def test_authentication_flow_known_client_id(setup_test_server):
    # Follow the full authentication flow on 401 and ensure all steps are executed
    session = VOAuthSession()

    matchers = setup_test_server(
        registered_client_id="known-client",
        registered_client_secret="known-secret",
    )

    (resource_matcher, rs_metadata_matcher, _openid_matcher,
     as_metadata_matcher, register_matcher, authorization_matcher, token_matcher) = matchers
    response = session.get("https://example.com/tap",
                           client_id = "known-client",
                           client_secret = "known-secret"
    )

    # Ensure the final contact is successful
    assert response.status_code == 200
    assert response.text == "secret data"

    # Called on 401 and after authentication
    assert resource_matcher.call_count == 2
    # All auth endpoints have been contacted once for auth flow
    assert rs_metadata_matcher.called_once
    assert as_metadata_matcher.called_once
    assert register_matcher.call_count == 0 # Dynamic registration skipped
    assert authorization_matcher.called_once
    assert token_matcher.called_once

    # Ensure client details and token are cached
    stored_session = session.session_store["https://example.com/tap"]
    assert stored_session.client_id == "known-client"
    assert stored_session.token["access_token"] == "correcttoken"
    assert (session.session_store.get_client_secret_for_url(
        "https://example.com/tap") == "known-secret")
