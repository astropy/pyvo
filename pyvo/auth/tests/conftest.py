from contextlib import contextmanager

import pytest
import requests_mock


class ContextAdapter(requests_mock.Adapter):
    """
    requests_mock adapter where ``register_uri`` returns a context manager
    """
    @contextmanager
    def register_uri(self, *args, **kwargs):
        matcher = super().register_uri(*args, **kwargs)

        yield matcher

        self.remove_matcher(matcher)

    def remove_matcher(self, matcher):
        if matcher in self._matchers:
            self._matchers.remove(matcher)


@pytest.fixture(scope='function')
def mocker():
    with requests_mock.Mocker(
        adapter=ContextAdapter(case_sensitive=True)
    ) as mocker_ins:
        yield mocker_ins

# Attempt to import oauth2 related modules for the below mocks. If import fails
# then the extra packages required for oauth2 are not installed
try:
    from pyvo.auth.oauth2 import sessionstore
    from pyvo.auth.tests.mocks import MockKeyring
    _OAUTH2_PACKAGES_INSTALLED = True
except ImportError:
    _OAUTH2_PACKAGES_INSTALLED = False


@pytest.fixture(autouse=True)
def fake_keyring(monkeypatch):
    # Initializes a mock keyring module for each test. No-op when the
    # oauth2 extra is not installed
    if _OAUTH2_PACKAGES_INSTALLED:
        monkeypatch.setattr(sessionstore, 'keyring', MockKeyring())
