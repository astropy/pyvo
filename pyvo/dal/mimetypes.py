# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
A module for parsing and working with mimetypes
"""

import mimetypes
import mimeparse

import six


mimetypes.add_type('application/fits', 'fits')
mimetypes.add_type('application/x-fits', 'fits')
mimetypes.add_type('image/fits', 'fits')
mimetypes.add_type('image/fits', 'fits')


def mime2extension(mimetype, default=None):
    """
    return a recommended file extension for a file with a given MIME-type.

    This function provides some generic mappings that can be leveraged in
    implementations of ``suggest_extension()`` in ``Record`` subclasses.

      >>> mime2extension('application/fits')
      fits
      >>> mime2extension('image/jpeg')
      jpg
      >>> mime2extension('application/x-zed', 'dat')
      dat

    Parameters
    ----------
    mimetype : str
       the file MIME-type byte-string to convert
    default : str
       the default extension to return if one could not be
       recommended based on ``mimetype``.  By convention,
       this should not include a preceding '.'

    Returns
    -------
    str
       the recommended extension without a preceding '.', or the
       value of ``default`` if no recommendation could be made.
    """
    if not mimetype:
        return default

    if type(mimetype) == six.text_type:
        mimetype = mimetype.encode('utf-8')

    ext = mimetypes.guess_extension(mimetype, strict=False)
    return ext
