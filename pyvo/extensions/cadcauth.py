import logging
import os

import requests
import requests.auth

class CADCAuth(requests.auth.AuthBase):

    def __init__(self):
        self.cookie = None

    def login(self, user, password, url='https://ws-cadc.canfar.net/ac/login'):
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
        self.cookie = '\"' + response.text + '\"'

    def __call__(self, request):
        request.prepare_cookies({'CADC_SSO': self.cookie})
        return request
