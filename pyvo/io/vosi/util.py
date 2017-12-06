# Licensed under a 3-clause BSD style license - see LICENSE.rst

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from astropy.extern import six

from astropy.utils.misc import InheritDocstrings

from astropy.io.votable.exceptions import warn_or_raise

__all__ = [
    "make_add_complexcontent", "make_add_simplecontent", "Element",
    "ValueMixin"]

def make_add_complexcontent(
        self, element_name, attr_name, cls_, exc_class=None):
    """
    Factory for generating add functions for elements with complex content.
    """
    def add_complextcontent(iterator, tag, data, config, pos):
        attr = getattr(self, attr_name)
        element = cls_(
            config=config, pos=pos, _element_name=element_name, **data)

        if attr and exc_class is not None:
            warn_or_raise(
                exc_class, args=element_name,
                config=config, pos=pos)

        if isinstance(getattr(self, attr_name), list):
            getattr(self, attr_name).append(element)
        else:
            setattr(self, attr_name, element)

        element.parse(iterator, config)

    return add_complextcontent

def make_add_simplecontent(
        self, element_name, attr_name, exc_class=None, check_func=None,
        data_func=None):
    """
    Factory for generating add functions for elements with simple content.
    This means elements with no child elements.
    If warning_class is given, warn or raise if element was already set.
    """
    def add_simplecontent(iterator, tag, data, config, pos):
        for start, tag, data, pos in iterator:
            if not start and tag == element_name:
                attr = getattr(self, attr_name)

                if all((
                        attr is not None and len(attr),
                        exc_class is not None
                )):
                    warn_or_raise(
                        exc_class, args=self._element_name,
                        config=config, pos=pos)
                if check_func:
                    check_func(data, config, pos)
                if data_func:
                    data = data_func(data)

                if isinstance(getattr(self, attr_name), list):
                    getattr(self, attr_name).append(data)
                else:
                    setattr(self, attr_name, data or None)
                break

    return add_simplecontent

@six.add_metaclass(InheritDocstrings)
class Element(object):
    """
    A base class for all classes that represent XML elements.

    Subclasses and Mixins must initialize their independent attributes after
    calling ``super().__init__``.
    """
    _element_name = ''

    def __init__(self, config=None, pos=None, _element_name='', **kwargs):
        if config is None:
            config = {}
        self._config = config
        self._pos = pos

        if _element_name:
            self._element_name = _element_name

        self._tag_mapping = {}

    def _add_unknown_tag(self, iterator, tag, data, config, pos):
        pass # TODO: warn_or_raise(W02, W02, tag, config, pos)

    def _ignore_add(self, iterator, tag, data, config, pos):
        pass

    def parse(self, iterator, config):
        """
        For internal use. Parse the XML content of the children of the element.
        Override this method and do after-parse checks after calling
        ``super().parse``, if you need to.

        Parameters
        ----------
        iterator : xml iterator
            An iterator over XML elements as returned by
            `~astropy.utils.xml.iterparser.get_xml_iterator`.
        config : dict
            The configuration dictionary that affects how certain
            elements are read.
        """
        for start, tag, data, pos in iterator:
            if start:
                self._tag_mapping.get(tag, self._add_unknown_tag)(
                    iterator, tag, data, config, pos)
            else:
                if tag == self._element_name:
                    if hasattr(self, "value"):
                        # for elements with simple content
                        setattr(self, "value", data or None)
                    break


class ValueMixin(object):
    """
    Mixin class for elements with inner content.
    """
    def __init__(self, config=None, pos=None, **kwargs):
        super(ValueMixin, self).__init__(config=config, pos=pos, **kwargs)
        self._value = None

    def __bool__(self):
        return bool(self.value)

    def _value_check(self, value):
        pass

    def _value_parse(self, value):
        return value

    @property
    def value(self):
        """The inner content of the element."""
        return self._value

    @value.setter
    def value(self, value):
        self._value_check(value)
        self._value = self._value_parse(value)
