import logging
import os

import requests
import requests.auth

class GaiaAuth(requests.auth.AuthBase):

    def __init__(self):
        self.cookies = None

    def login(self, user, password, url='http://gea.esac.esa.int/tap-server/login'):
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'text/plain'
        }

        data = {
            'username': user,
            'password': password
        }

        response = requests.post(url, data=data, headers=headers)
        response.raise_for_status()
        logging.debug(response.cookies)
        self.cookies = response.cookies

    def __call__(self, request):
        request.cookies = self.cookies
        return request
