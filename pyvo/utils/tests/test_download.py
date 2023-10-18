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
import urllib

from astropy.utils.data import get_pkg_data_contents

from pyvo.utils.download import (_filename_from_url, PyvoUserWarning, _s3_is_accessible,
                                 http_download, aws_download)

try:
    # Both boto3, botocore and moto are optional dependencies, but the former 2 are
    # dependencies of the latter, so it's enough to handle them with one variable
    import boto3
    from botocore.exceptions import ClientError
    from moto import mock_s3
    HAS_MOTO = True
except ImportError:
    HAS_MOTO = False


# Useful variables
# For http_download:
get_pkg_data_contents = partial(
   get_pkg_data_contents, package=__package__, encoding='binary')
data_re = re.compile('http://example.com/data.*')
# For aws_download:
s3_bucket = 'pyvo-bucket'
s3_key = 'key1/key2/somekey.txt'


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
        fname = request.path.split('/')[-1]
        return get_pkg_data_contents(f'data/{fname}')

    with mocker.register_uri(
        'GET', data_re, content=callback, headers={'content-length':'901'},
    ) as matcher:
        yield matcher


def test_http_download__noPath(http_mock):
    filename = http_download('http://example.com/data/basic.xml',
                             local_filepath=None, cache=False)
    assert(filename == 'basic.xml')
    os.remove('basic.xml')


def test_http_download__noFile(http_mock):
    with pytest.raises(urllib.error.URLError):
        filename = http_download('http://example.com/data/nofile.fits')


def test_http_download__wPath(http_mock):
    filename = http_download('http://example.com/data/basic.xml',
                             local_filepath='basic2.xml', cache=False)
    assert(filename == 'basic2.xml')
    assert(os.path.exists('basic2.xml'))
    os.remove('basic2.xml')


def test_http_download__wrong_cache(http_mock):
    # get the file first
    with open('basic.xml', 'w') as fp:
        fp.write('some content')
    # get it from cache
    with pytest.warns(PyvoUserWarning):
        filename = http_download('http://example.com/data/basic.xml',
                                 local_filepath='basic.xml', cache=True)
    assert(os.path.getsize('basic.xml') == 901)
    os.remove('basic.xml')



@pytest.mark.skipif('not HAS_MOTO')
@pytest.fixture(name='s3_mock')
def _s3_mock(mocker):
    with mock_s3():
        conn = boto3.resource('s3', region_name='us-east-1')
        conn.create_bucket(Bucket=s3_bucket)
        s3_client = conn.meta.client
        s3_client.put_object(Bucket=s3_bucket, Key=s3_key, Body='my content')
        yield conn


@pytest.mark.skipif('not HAS_MOTO')
def test_s3_mock_basic(s3_mock):
    s3 = s3_mock.meta.client
    body = s3_mock.Object(s3_bucket, s3_key).get()['Body']
    content = body.read().decode('utf-8')
    assert content == 'my content'


@pytest.mark.skipif('not HAS_MOTO')
def test__s3_is_accessible_yes(s3_mock):
    accessible, exc = _s3_is_accessible(s3_mock, s3_bucket, s3_key)
    assert(accessible)
    assert(exc is None)


@pytest.mark.skipif('not HAS_MOTO')
def test__s3_is_accessible_no_bucket(s3_mock):
    accessible, exc = _s3_is_accessible(s3_mock, 'some-bucket', s3_key)
    assert(not accessible)
    assert('NoSuchBucket' in str(exc))


@pytest.mark.skipif('not HAS_MOTO')
def test__s3_is_accessible_no_key(s3_mock):
    accessible, exc = _s3_is_accessible(s3_mock, s3_bucket, 'does/not/exist')
    assert(not accessible)
    assert(isinstance(exc, ClientError))
    errmsg = str(exc)
    assert('Not Found' in errmsg and '404' in errmsg)


@pytest.mark.skipif('not HAS_MOTO')
def test_s3_download__noPath(s3_mock):
    filename = aws_download(f's3://{s3_bucket}/{s3_key}',
                             local_filepath=None, cache=False)
    fname = s3_key.split('/')[-1]
    assert(filename == fname)
    os.remove(fname)


@pytest.mark.skipif('not HAS_MOTO')
def test_s3_download__noKey(s3_mock):
    with pytest.raises(ClientError):
        filename = aws_download(f's3://{s3_bucket}/does/not/exist')


@pytest.mark.skipif('not HAS_MOTO')
def test_s3_download__wPath(s3_mock):
    filename = aws_download(f's3://{s3_bucket}/{s3_key}',
                             local_filepath='newkey.txt', cache=False)
    assert(filename == 'newkey.txt')
    assert(os.path.exists('newkey.txt'))
    os.remove(filename)


@pytest.mark.skipif('not HAS_MOTO')
def test_aws_download__wrong_cache(s3_mock):
    # get the file first
    with open('somekey.txt', 'w') as fp:
        fp.write('not my content')
    # get it from cache
    with pytest.warns(PyvoUserWarning):
        filename = aws_download(f's3://{s3_bucket}/{s3_key}',
                                local_filepath='somekey.txt', cache=True)
    assert(os.path.getsize('somekey.txt') == 10)
    os.remove('somekey.txt')
