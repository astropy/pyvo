import collections
import logging

import requests

from .authurls import AuthURLs
from .credstore import CredStore

class AuthSession(requests.Session):

    def __init__(self):
        super(AuthSession, self).__init__()
        self.auth_urls = AuthURLs()
        self.creds = CredStore()

    def attach(self, service):
        logging.debug('Attaching to %s', service)
        service.session = self
        self.auth_urls.parse_capabilities(service.capabilities)

    def get(self, url, **kwargs):
        self._patch_args(url, kwargs)
        return super(AuthSession, self).get(url, **kwargs)

    def options(self, url, **kwargs):
        self._patch_args(url, kwargs)
        return super(AuthSession, self).options(url, **kwargs)

    def head(self, url, **kwargs):
        self._patch_args(url, kwargs)
        return super(AuthSession, self).head(url, **kwargs)

    def post(self, url, **kwargs):
        self._patch_args(url, kwargs)
        return super(AuthSession, self).post(url, **kwargs)

    def put(self, url, data=None, **kwargs):
        self._patch_args(url, kwargs)
        return super(AuthSession, self).put(url, **kwargs)

    def patch(self, url, data=None, **kwargs):
        self._patch_args(url, kwargs)
        return super(AuthSession, self).patch(url, **kwargs)

    def delete(self, url, **kwargs):
        self._patch_args(url, kwargs)
        return super(AuthSession, self).delete(url, **kwargs)

    def _patch_args(self, url, kwargs):
        methods = self.auth_urls.allowed_auth_methods(url)
        logging.debug('Possible auth methods: %s', methods)

        negotiated_method = self.creds.negotiate_method(methods)
        logging.debug('Using auth method: %s', negotiated_method)

        authenticator = self.creds.get_authenticator(negotiated_method)
        kwargs.setdefault('auth', authenticator)
