import logging

import requests

class CredStore(object):

    def __init__(self):
        self.credentials = {'anonymous': None}

    def negotiate_method(self, allowed_methods):
        available_methods = set(self.credentials.keys())
        methods = available_methods.intersection(allowed_methods)
        logging.debug('Available methods: %s', methods)

        # If there are more than 1 method to pick, don't pick
        # anonymous over an actual method.
        if len(methods) > 1:
            methods.discard('anonymous')

        # Pick a random method.
        return methods.pop()

    def add_authenticator(self, method_uri, authenticator):
        self.credentials[method_uri] = authenticator

    def get_authenticator(self, method_uri):
        return self.credentials[method_uri]
