# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
URL utils
"""
from __future__ import (
    absolute_import, division, print_function, unicode_literals)

from six.moves.urllib.parse import urlparse, urlunparse
from os.path import split as pathsplit, join as pathjoin


def url_sibling(url, sibling):
    parsed = urlparse(url)
    newpath = pathjoin(*pathsplit(parsed.path)[:-1], sibling)
    return urlunparse(list(parsed[:2]) + [newpath] + list(parsed[3:]))
