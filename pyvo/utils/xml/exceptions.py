# Licensed under a 3-clause BSD style license - see LICENSE.rst

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from warnings import warn

from astropy.utils.exceptions import AstropyWarning

__all__ = ['XMLWarning', 'UnknownElementWarning']

MAX_WARNINGS = 10


def _format_message(message, name, config=None, pos=None):
    if config is None:
        config = {}
    if pos is None:
        pos = ('?', '?')
    filename = config.get('filename', '?')

    return '{}:{}:{}: {}: {}'.format(filename, pos[0], pos[1], name, message)


def warn_or_raise(warning_class, exception_class=None, args=(), config=None,
                  pos=None, stacklevel=1):
    """
    Warn or raise an exception, depending on the pedantic setting.
    """
    if config is None:
        config = {}
    if config.get('pedantic'):
        if exception_class is None:
            exception_class = warning_class
        raise_(exception_class, args, config, pos)
    else:
        warn_(warning_class, args, config, pos, stacklevel=stacklevel+1)


def raise_(exception_class, args=(), config=None, pos=None):
    """
    Raise an exception, with proper position information if available.
    """
    if config is None:
        config = {}
    raise exception_class(args, config, pos)


def reraise(exc, config=None, pos=None, additional=''):
    """
    Raise an exception, with proper position information if available.
    Restores the original traceback of the exception, and should only
    be called within an "except:" block of code.
    """
    if config is None:
        config = {}
    message = _format_message(str(exc), exc.__class__.__name__, config, pos)
    if message.split()[0] == str(exc).split()[0]:
        message = str(exc)
    if len(additional):
        message += ' ' + additional
    exc.args = (message,)
    raise exc


def _suppressed_warning(warning, config, stacklevel=2):
    warning_class = type(warning)
    config.setdefault('_warning_counts', dict()).setdefault(warning_class, 0)
    config['_warning_counts'][warning_class] += 1
    message_count = config['_warning_counts'][warning_class]
    if message_count <= MAX_WARNINGS:
        if message_count == MAX_WARNINGS:
            warning.formatted_message += (
                ' (suppressing further warnings of this type...)')
        warn(warning, stacklevel=stacklevel+1)


def warn_unknown_attrs(
        element, attrs, config, pos, good_attr=[], stacklevel=1):
    for attr in attrs:
        if attr not in good_attr:
            warn_(
                UnknownAttributeWarning, (attr, element), config, pos,
                stacklevel=stacklevel+1)


def warn_(warning_class, args=(), config=None, pos=None, stacklevel=1):
    """
    Warn, with proper position information if available.
    """
    if config is None:
        config = {}
    warning = warning_class(args, config, pos)
    _suppressed_warning(warning, config, stacklevel=stacklevel+1)


class XMLWarning(AstropyWarning):
    """
    Base warning for violations of XML specifications
    """
    def __init__(self, args, config=None, pos=None):
        if config is None:
            config = {}
        if not isinstance(args, tuple):
            args = (args, )
        msg = self.message_template.format(*args)

        self.formatted_message = _format_message(
            msg, self.__class__.__name__, config, pos)
        Warning.__init__(self, self.formatted_message)


class UnknownElementWarning(XMLWarning):
    """
    Warning for missing xml elements
    """
    message_template = "Unknown element {}"
    default_args = ('x',)


class UnknownAttributeWarning(XMLWarning):
    """
    Warning for missing xml attributes
    """
    message_template = "Unknown attribute {}"
    default_args = ('x',)
