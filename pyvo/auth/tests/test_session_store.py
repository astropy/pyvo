"""
Tests for pyvo.auth.oauth2 session storage (SessionStore).
"""

import pytest
import requests
import keyring
from requests_oauthlib import OAuth2Session

from ..oauth2 import sessionstore
from ..oauth2.sessionstore import SessionStore

class MockKeyring:
    """Mock for keyring"""

    errors = keyring.errors

    def __init__(self):
        self.storage = {}

    def set_password(self, service, username, password):
        self.storage[(service, username)] = password

    def get_password(self, service, username):
        return self.storage.get((service, username))

    def delete_password(self, service, username):
        try:
            del self.storage[(service, username)]
        except KeyError as exc:
            raise keyring.errors.PasswordDeleteError(username) from exc


@pytest.fixture
def store(monkeypatch):
    monkeypatch.setattr(sessionstore, 'keyring', MockKeyring())
    return SessionStore('pyvo-test-keystore')

# Tests
def test_exact_match_takes_priority(store):
    exact = OAuth2Session('exact')
    prefix = OAuth2Session('prefix')
    store.add_session_for_url('https://example.com/', prefix)
    store.add_session_for_url('https://example.com/tap', exact, exact=True)
    assert store.get_session_for_url('https://example.com/tap') is exact

def test_most_specific_url_session_returned(store):
    short = OAuth2Session('short')
    long = OAuth2Session('long')
    store.add_session_for_url('https://example.com/', short)
    store.add_session_for_url('https://example.com/tap/', long)
    assert store.get_session_for_url('https://example.com/tap/sync') is long
    assert store.get_session_for_url('https://example.com/scs') is short

def test_anonymous_session_returned_if_allowed(store):
    should_be_anonymous = store.get_session_for_url("https://example.com/tap", True)
    assert isinstance(should_be_anonymous, requests.Session)
    assert should_be_anonymous.auth is None

def test_no_anonymous_fallback_returns_none(store):
    assert store.get_session_for_url('https://other.com/tap', False) is None

def test_getitem_returns_session(store):
    store.add_session_for_url(
        'https://example.com/',
        OAuth2Session('client-id')
    )
    assert store['https://example.com/tap'].client_id == 'client-id'

def test_getitem_raises_key_error(store):
    with pytest.raises(KeyError):
        store['https://pluto.com/tap']

def test_client_secret_storage(store):
    store.add_session_for_url(
        'https://example.com/',
        OAuth2Session('client-id')
    )
    store.add_client_secret_for_url('https://example.com/tap', 'secret')
    assert store.get_client_secret_for_url('https://example.com/tap') == 'secret'

    store.delete_client_secret_for_url('https://example.com/tap')
    assert store.get_client_secret_for_url('https://example.com/tap') is None


def test_client_secret_requires_client_id(store):
    store.add_session_for_url(
        'https://example.com/',
            OAuth2Session(client_id=None)
        )
    with pytest.raises(ValueError):
        store.add_client_secret_for_url('https://example.com/tap', 'secret')
    with pytest.raises(ValueError):
        store.get_client_secret_for_url('https://example.com/tap')
    with pytest.raises(ValueError):
        store.delete_client_secret_for_url('https://example.com/tap')

def test_add_session_stores_client_secret(store):
    store.add_session_for_url(
        'https://example.com/',
        OAuth2Session( client_id='client-id'),
        client_secret='secret'
    )
    assert store.get_session_for_url('https://example.com/').client_id == "client-id"
    assert store.get_client_secret_for_url('https://example.com/') == 'secret'
