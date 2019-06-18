import logging
import os

import requests.auth

class LSSTAuth(requests.auth.AuthBase):
    def __call__(self, r):
        r.headers['Authorization'] = 'Bearer ' + os.environ['ACCESS_TOKEN']
        r.prepare_cookies({'oauth2_proxy': os.environ['ACCESS_TOKEN']})
        logging.debug(r.headers)
        return r
