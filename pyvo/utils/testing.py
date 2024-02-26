# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Shared utilities for unit (and not-so-unit) tests.

TODO: perhaps move the contents of pyvo.registry.tests.conftest here, too?
"""

import base64
import hashlib
import inspect
import os
import pickle
from urllib import parse as urlparse

import requests
import requests_mock


def get_digest(data):
    """returns a hash-type string for data.

    Parameters
    ----------

    data : a string (in which case the utf-8-encoding will be hashed)
        or bytes of which to generate the hash


    Returns
    -------

    str
        a reasonably unique message digest of ``data``.  This is currently
        a piece of the b64 encoding of an md5 digest of data, so don't even
        think of doing anything cryptographic with this.
    """
    if isinstance(data, str):
        data = data.encode("utf-8")

    # requests has random mime/multipart separators.  Heuristically
    # try to remove them so we get constant hashes; to do
    # this properly, we'd have to look at the request headers
    # and extract the boundary string from there.  Let's
    # see if we can get away with detecting form data and then
    # just use the first line.
    if b"Content-Disposition: form-data" in data:
        boundary = data.split(b"\r", 1)[0]
        data = data.replace(boundary, b"")

    return base64.b64encode(
        hashlib.md5(data).digest(), b"+%"
        ).decode("ascii")[:8]


def hashify_request_payload(data):
    """returns a hash for a data/params argument in request.

    That could be: Dictionary, list of tuples, bytes or file-like object
    """
    if isinstance(data, (bytes, str)):
        return get_digest(data)

    elif isinstance(data, list):
        return get_digest(urlparse.urlencode(sorted(data)))

    else:
        raise ValueError(f"Cannot compute a hash of '{data}'")


class LearnableRequestMocker(requests_mock.Mocker):
    def __init__(self, fixture_name, *, learning=False):
        super().__init__()

        # find the caller's file's location; we use this to have
        # a convenient place for our cached data.
        test_source = inspect.currentframe().f_back.f_code.co_filename
        self.response_dir = os.path.join(
            os.path.dirname(test_source), "data",
            fixture_name)
        os.makedirs(self.response_dir, exist_ok=True)

    def _get_cache_name(self, method, url, payload):
        """returns a file name for a request characterised by our
        arguments.

        The plan is that we have a manageable file name that is uniquely
        derivable from the arguments and yet gives folks a chance to match
        it up with requests in their code.

        payload is either a query string or a request payload or None.
        It's used to produce a unique hash, and the first characters
        for the query string are in the file name to make it simpler
        to find responses.
        """
        payload_hash = hashify_request_payload(payload
            ) if payload else ""
        parsed = urlparse.urlparse(url)
        last_segment = parsed.path.split("/")[-1]
        urlhash = get_digest(url)

        return os.path.join(
            self.response_dir,
            f"{method}-{parsed.netloc}-{last_segment}"
            f"-{urlhash}{payload_hash}")

    def pickle_response(self, request, response, cache_name):
        # requests will already have dealt with content-encoding,
        # so we have to drop it
        response.headers.pop("Content-Encoding", None)

        meta = {
            "status_code": response.status_code,
            "headers": response.headers,
            "request": request}
        with open(cache_name+".meta", "wb") as f:
            pickle.dump(meta, f)
        with open(cache_name, "wb") as f:
            f.write(response.content)

        return self.unpickle_response(cache_name)

    def unpickle_response(self, cache_name):
        with open(cache_name+".meta", "rb") as f:
            meta = pickle.load(f)
        with open(cache_name, "rb") as f:
            meta["content"] = f.read()

        return requests_mock.create_response(**meta)

    def __call__(self, request):
        # we need to be specific in what arguments we get, because
        # we turn then into file names.  Hence, every requests feature
        # we want to support needs changes in our request method's
        # signature.
        method, url, data, params = \
            request.method, request.url, request.text, request.qs

        # we have to try to make the request payload (if any)
        # as reproducable as possible, which is why we're trying
        # to sort by parameter name
        payload = ""
        if params:
            assert not data
            payload = "&".join(f"{k}={v}" for k, v in sorted(
                params.items()))
        if data:
            assert not params
            payload = "&".join(p for p in sorted(data.split("&")))

        cache_name = self._get_cache_name(method, url, payload)
        if os.path.exists(cache_name):
            return self.unpickle_response(cache_name)

        else:
            # No stored response available; try to fetch one from
            # the network.  This will without remote-data enabled,
            # which is a nice benefit: When you have broken something
            # in a way that it will query extra services, the normal
            # test will fail.
            #
            # We can't just fall through to real_http here, since
            # we need the response object in order to pickle it.
            # Given that, we have dig into requests_mock's guts;
            # I don't think we can retrieve the original session
            # from here except by pulling it from the stack; until
            # we actually need it, just make a new session.
            response = requests_mock.mocker._original_send(
                requests.Session(), request)
            # TODO: figure out some way to inject failures into the cache.
            # I'm pretty sure we don't want to blindly store failures
            # that occur during learning.
            return self.pickle_response(request, response, cache_name)
