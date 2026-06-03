#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.auth
"""
import base64
from requests.cookies import RequestsCookieJar
from string import Template

import pytest

from astropy.utils.data import get_pkg_data_contents

import pyvo.dal
from pyvo.auth.authsession import AuthSession
from pyvo.auth.authurls import AuthURLs
from pyvo.auth import securitymethods

from pyvo.dal.tests.test_tap import MockAsyncTAPServer
from pyvo.utils.http import create_session


@pytest.fixture(name='security_methods')
def _security_methods():
    return [None]


@pytest.fixture()
def auth_capabilities(mocker, security_methods):
    anon_element = '<securityMethod />'
    sm_element = Template('<securityMethod standardID="$m" />')
    method_elements = []

    for m in security_methods:
        if m is None:
            method_elements.append(anon_element)
        else:
            method_elements.append(sm_element.substitute(m=m))

    def callback(request, context):
        t = Template(get_pkg_data_contents('data/tap/capabilities.xml'))
        capabilities = t.substitute(security_methods=method_elements)
        return capabilities.encode('utf-8')

    with mocker.register_uri(
        'GET', 'http://example.com/tap/capabilities', content=callback
    ) as matcher:
        yield matcher


class MockAnonAuthTAPServer(MockAsyncTAPServer):
    def validator(self, request):
        assert request.cert is None
        assert 'Authorization' not in request.headers
        assert 'Cookie' not in request.headers


@pytest.fixture()
def anon_auth_service(mocker):
    yield from MockAnonAuthTAPServer().use(mocker)


class MockCookieAuthTAPServer(MockAsyncTAPServer):
    def validator(self, request):
        assert request.cert is None
        assert 'Authorization' not in request.headers
        assert request.headers.get('Cookie', None) == 'TEST_COOKIE=BADCOOKIE'


@pytest.fixture()
def cookie_auth_service(mocker):
    yield from MockCookieAuthTAPServer().use(mocker)


class MockCertificateAuthTAPServer(MockAsyncTAPServer):
    def validator(self, request):
        assert request.cert == 'client-certificate.pem'
        assert 'Authorization' not in request.headers
        assert 'Cookie' not in request.headers


@pytest.fixture()
def certificate_auth_service(mocker):
    yield from MockCertificateAuthTAPServer().use(mocker)


class MockBasicAuthTAPServer(MockAsyncTAPServer):
    def validator(self, request):
        pw = b'testuser:hunter2'
        basic_encoded = 'Basic ' + base64.b64encode(pw).decode('ascii')

        assert request.cert is None
        assert request.headers.get('Authorization', None) == basic_encoded
        assert 'Cookie' not in request.headers


@pytest.fixture()
def basic_auth_service(mocker):
    yield from MockBasicAuthTAPServer().use(mocker)


@pytest.fixture()
def bearer_token_tables(mocker):
    def callback(request, context):
        assert request.headers.get('Authorization', None) == 'Bearer mytoken'
        return get_pkg_data_contents('data/tap/tables.xml').encode('utf-8')

    with mocker.register_uri(
        'GET', 'http://example.com/tap/tables', content=callback
    ):
        yield


@pytest.mark.usefixtures('cookie_auth_service', 'auth_capabilities')
@pytest.mark.parametrize('security_methods', [[None, 'ivo://ivoa.net/sso#cookie']])
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W27")
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W48")
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W06")
def test_cookies_auth():
    session = AuthSession()
    session.credentials.set_cookie('TEST_COOKIE', 'BADCOOKIE')
    service = pyvo.dal.TAPService('http://example.com/tap', session=session)
    service.run_async("SELECT * FROM ivoa.obscore")


@pytest.mark.usefixtures('cookie_auth_service', 'auth_capabilities')
@pytest.mark.parametrize('security_methods', [[None, 'ivo://ivoa.net/sso#cookie']])
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W27")
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W48")
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W06")
def test_cookie_jar_auth():
    session = AuthSession()
    jar = RequestsCookieJar()
    jar.set('TEST_COOKIE', 'BADCOOKIE')
    session.credentials.set_cookie_jar(jar)
    service = pyvo.dal.TAPService('http://example.com/tap', session=session)
    service.run_async("SELECT * FROM ivoa.obscore")


@pytest.mark.usefixtures('certificate_auth_service', 'auth_capabilities')
@pytest.mark.parametrize('security_methods', [[None, 'ivo://ivoa.net/sso#tls-with-certificate']])
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W27")
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W48")
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W06")
def test_certificate_auth():
    session = AuthSession()
    session.credentials.set_client_certificate('client-certificate.pem')
    service = pyvo.dal.TAPService('http://example.com/tap', session=session)
    service.run_async("SELECT * FROM ivoa.obscore")


@pytest.mark.usefixtures('basic_auth_service', 'auth_capabilities')
@pytest.mark.parametrize('security_methods', [[None, 'ivo://ivoa.net/sso#BasicAA']])
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W27")
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W48")
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W06")
def test_basic_auth():
    session = AuthSession()
    session.credentials.set_password('testuser', 'hunter2')
    service = pyvo.dal.TAPService('http://example.com/tap', session=session)
    service.run_async("SELECT * FROM ivoa.obscore")


@pytest.mark.usefixtures('basic_auth_service', 'auth_capabilities')
@pytest.mark.parametrize('security_methods', [[None, 'ivo://ivoa.net/sso#BasicAA']])
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W27")
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W48")
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W06")
def test_negotiation():
    session = AuthSession()
    session.credentials.set_password('testuser', 'hunter2')
    session.credentials.set_client_certificate('client-certificate.pem')
    session.credentials.set_cookie('TEST_COOKIE', 'BADCOOKIE')
    service = pyvo.dal.TAPService('http://example.com/tap', session=session)
    service.run_async("SELECT * FROM ivoa.obscore")


class TestAuthURLs:
    """Unit tests for AuthURLs prefix/capability matching semantics."""

    def test_capability_does_not_override_prefix_registration(self):
        auth = AuthURLs()
        auth.add_security_method_for_url('http://example.com/tap', 'custom-token')
        auth._add_capability_method(
            'http://example.com/tap/tables', 'ivo://ivoa.net/sso#cookie'
        )

        methods = auth.allowed_auth_methods('http://example.com/tap/tables')
        assert 'custom-token' in methods
        assert 'ivo://ivoa.net/sso#cookie' in methods

    def test_prefix_registration_propagates_to_all_subpaths(self):
        auth = AuthURLs()
        auth.add_security_method_for_url('http://example.com/tap', 'custom-token')

        for sub in ('/sync', '/async', '/tables', '/tables/schema'):
            methods = auth.allowed_auth_methods(
                'http://example.com/tap' + sub
            )
            assert 'custom-token' in methods, f"missing for {sub}"

    def test_multiple_prefix_registrations_are_unioned(self):
        auth = AuthURLs()
        auth.add_security_method_for_url('http://example.com/tap', 'token-a')
        auth.add_security_method_for_url('http://example.com/tap/v2', 'token-b')

        methods = auth.allowed_auth_methods('http://example.com/tap/v2/sync')
        assert 'token-a' in methods
        assert 'token-b' in methods

    def test_most_specific_capability_wins_over_less_specific(self):
        auth = AuthURLs()
        auth._add_capability_method(
            'http://example.com/tap', 'ivo://ivoa.net/sso#cookie'
        )
        auth._add_capability_method(
            'http://example.com/tap/tables', 'ivo://ivoa.net/sso#BasicAA'
        )

        methods = auth.allowed_auth_methods('http://example.com/tap/tables')
        assert 'ivo://ivoa.net/sso#BasicAA' in methods
        assert 'ivo://ivoa.net/sso#cookie' not in methods

    def test_exact_match_overrides_all(self):
        auth = AuthURLs()
        auth.add_security_method_for_url('http://example.com/tap', 'custom-token')
        auth._add_capability_method(
            'http://example.com/tap/tables', 'ivo://ivoa.net/sso#cookie'
        )
        auth.add_security_method_for_url(
            'http://example.com/tap/tables', securitymethods.ANONYMOUS, exact=True
        )

        methods = auth.allowed_auth_methods('http://example.com/tap/tables')
        assert methods == {securitymethods.ANONYMOUS}

    def test_no_match_returns_anonymous(self):
        auth = AuthURLs()
        methods = auth.allowed_auth_methods('http://example.com/unknown')
        assert methods == {securitymethods.ANONYMOUS}


@pytest.mark.usefixtures('bearer_token_tables', 'auth_capabilities')
@pytest.mark.parametrize('security_methods', [
    ['ivo://ivoa.net/sso#BasicAA',
     'ivo://ivoa.net/sso#cookie',
     'ivo://ivoa.net/sso#OAuth']
])
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W27")
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W48")
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W06")
def test_bearer_token_auth():
    session = AuthSession()
    credentials = create_session()
    credentials.headers["Authorization"] = "Bearer mytoken"
    session.credentials.set("my-token", credentials)
    session.add_security_method_for_url("http://example.com/tap", "my-token")
    service = pyvo.dal.TAPService('http://example.com/tap', session=session)
    _ = service.tables


@pytest.mark.usefixtures('anon_auth_service', 'auth_capabilities')
@pytest.mark.parametrize('security_methods', [[None, 'ivo://ivoa.net/sso#FancyAuth']])
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W27")
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W48")
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W06")
def test_no_common_auth_negotiation():
    session = AuthSession()
    session.credentials.set_password('testuser', 'hunter2')
    session.credentials.set_client_certificate('client-certificate.pem')
    session.credentials.set_cookie('TEST_COOKIE', 'BADCOOKIE')
    service = pyvo.dal.TAPService('http://example.com/tap', session=session)
    service.run_async("SELECT * FROM ivoa.obscore")
