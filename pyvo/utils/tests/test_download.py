# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.utils.download
"""
import os
from functools import partial
import re
import pytest
import requests_mock
from contextlib import contextmanager
from urllib.error import URLError


from astropy.utils.data import get_pkg_data_contents

from pyvo.utils.download import _filename_from_url, PyvoUserWarning, http_download




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




get_pkg_data_contents = partial(
   get_pkg_data_contents, package=__package__, encoding='binary')

data_re = re.compile('http://example.com/data.*')


def test__filename_from_url():
    urls = [
        'https://example.com/files/myfile.pdf?user_id=123',
        'https://example.com/files/myfile.pdf',
        'http://somesite.com/service?file=/location/myfile.pdf&size=large'
    ]
    
    for url in urls:
        filename = _filename_from_url(url)
        assert(filename == 'myfile.pdf')


@pytest.fixture(name='http_mock')
def _data_downloader(mocker):
    def callback(request, context):
        #print(context.headers);raise ValueError
        fname = request.path.split('/')[-1]
        return get_pkg_data_contents(f'data/{fname}')

    with mocker.register_uri(
        'GET', data_re, content=callback, headers={'content-length':'901'},
    ) as matcher:
        yield matcher

@pytest.mark.usefixtures('http_mock')
def test_http_download__noPath():
    filename = http_download('http://example.com/data/basic.xml', 
                             local_filepath=None, cache=False)
    assert(filename == 'basic.xml')
    os.remove('basic.xml')
    
@pytest.mark.usefixtures('http_mock')
def test_http_download__noFile():
    with pytest.raises(URLError):
        filename = http_download('http://example.com/data/nofile.fits')


@pytest.mark.usefixtures('http_mock')
def test_http_download__wPath():
    filename = http_download('http://example.com/data/basic.xml', 
                             local_filepath='basic2.xml', cache=False)
    assert(filename == 'basic2.xml')
    os.remove('basic2.xml')

@pytest.mark.usefixtures('http_mock')
def test_http_download__wrong_cache():
    # get the file first
    with open('basic.xml', 'w') as fp:
        fp.write('some content')
    # get it from cache
    with pytest.warns(PyvoUserWarning):
        filename = http_download('http://example.com/data/basic.xml', 
                                 local_filepath='basic.xml', cache=True)
    assert(os.path.getsize('basic.xml') == 901)
    os.remove('basic.xml')