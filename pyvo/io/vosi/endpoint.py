# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
This file contains a contains the high-level functions to read the various
VOSI Endpoints.
"""

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from astropy.extern import six

from astropy.utils.xml import iterparser
from astropy.utils.collections import HomogeneousList
from astropy.io.votable.exceptions import vo_raise, vo_warn
from astropy.io.votable.util import version_compare

from .util import make_add_complexcontent, Element
from . import voresource as vr
from . import vodataservice as vs
from . import tapregext as tr
from . import availability as av
from .exceptions import W15, W16, E07

__all__ = [
    "parse_tables", "parse_capabilities", "parse_availability",
    "TablesFile", "CapabilitiesFile", "AvailabilityFile"]

def parse_tables(source, pedantic=None, filename=None,
                 _debug_python_based_parser=False):
    """
    Parses a tableset xml file (or file-like object), and returns a
    `~pyvo.io.vosi.endpoint.TablesetFile` object.

    Parameters
    ----------
    source : str or readable file-like object
        Path or file object containing a tableset xml file.
    pedantic : bool, optional
        When `True`, raise an error when the file violates the spec,
        otherwise issue a warning.  Warnings may be controlled using
        the standard Python mechanisms.  See the `warnings`
        module in the Python standard library for more information.
        Defaults to False.
    filename : str, optional
        A filename, URL or other identifier to use in error messages.
        If *filename* is None and *source* is a string (i.e. a path),
        then *source* will be used as a filename for error messages.
        Therefore, *filename* is only required when source is a
        file-like object.

    Returns
    -------
    votable : `~pyvo.io.vosi.endpoint.TableSetFile` object

    See also
    --------
    pyvo.io.vosi.exceptions : The exceptions this function may raise.
    """
    config = {
        'pedantic': pedantic,
        'filename': filename
    }

    if filename is None and isinstance(source, six.string_types):
        config['filename'] = source

    with iterparser.get_xml_iterator(
        source,
        _debug_python_based_parser=_debug_python_based_parser) as iterator:
        return TablesFile(
            config=config, pos=(1, 1)).parse(iterator, config)

def parse_capabilities(source, pedantic=None, filename=None,
                       _debug_python_based_parser=False):
    """
    Parses a capabilities xml file (or file-like object), and returns a
    `~pyvo.io.vosi.endpoint.CapabilitiesFile` object.

    Parameters
    ----------
    source : str or readable file-like object
        Path or file object containing a capabilities xml file.
    pedantic : bool, optional
        When `True`, raise an error when the file violates the spec,
        otherwise issue a warning.  Warnings may be controlled using
        the standard Python mechanisms.  See the `warnings`
        module in the Python standard library for more information.
        Defaults to False.
    filename : str, optional
        A filename, URL or other identifier to use in error messages.
        If *filename* is None and *source* is a string (i.e. a path),
        then *source* will be used as a filename for error messages.
        Therefore, *filename* is only required when source is a
        file-like object.

    Returns
    -------
    votable : `~pyvo.io.vosi.endpoint.CapabilitiesFile` object

    See also
    --------
    pyvo.io.vosi.exceptions : The exceptions this function may raise.
    """
    config = {
        'pedantic': pedantic,
        'filename': filename
    }

    if filename is None and isinstance(source, six.string_types):
        config['filename'] = source

    with iterparser.get_xml_iterator(
        source,
        _debug_python_based_parser=_debug_python_based_parser) as iterator:
        return CapabilitiesFile(
            config=config, pos=(1, 1)).parse(iterator, config)

def parse_availability(source, pedantic=None, filename=None,
                       _debug_python_based_parser=False):
    """
    Parses a availability xml file (or file-like object), and returns a
    `~pyvo.io.vosi.endpoint.AvailabilityFile` object.

    Parameters
    ----------
    source : str or readable file-like object
        Path or file object containing a availability xml file.
    pedantic : bool, optional
        When `True`, raise an error when the file violates the spec,
        otherwise issue a warning.  Warnings may be controlled using
        the standard Python mechanisms.  See the `warnings`
        module in the Python standard library for more information.
        Defaults to False.
    filename : str, optional
        A filename, URL or other identifier to use in error messages.
        If *filename* is None and *source* is a string (i.e. a path),
        then *source* will be used as a filename for error messages.
        Therefore, *filename* is only required when source is a
        file-like object.

    Returns
    -------
    votable : `~pyvo.io.vosi.endpoint.AvailabilityFile` object

    See also
    --------
    pyvo.io.vosi.exceptions : The exceptions this function may raise.
    """
    config = {
        'pedantic': pedantic,
        'filename': filename
    }

    if filename is None and isinstance(source, six.string_types):
        config['filename'] = source

    with iterparser.get_xml_iterator(
        source,
        _debug_python_based_parser=_debug_python_based_parser) as iterator:
        return AvailabilityFile(
            config=config, pos=(1, 1)).parse(iterator, config)

class TablesFile(Element):
    """
    TABLESET/TABLE element: represents an entire file.
    The keyword arguments correspond to setting members of the same
    name, documented below.
    """

    def __init__(self, config=None, pos=None, version="1.1"):
        Element.__init__(self, config, pos)

        self.tableset = None
        self.table = None

        self._ntables = None

        version = str(version)
        if version not in ("1.0", "1.1"):
            raise ValueError("'version' should be one of '1.0' or '1.1'")

        config['version'] = version
        self._version = version

    def __repr__(self):
        if self.table:
            return repr(self.table)
        elif self.tableset:
            return repr(self.tableset)
        else:
            return super(TablesFile, self).__repr__()

    @property
    def version(self):
        """
        The version of the TableSet specification that the file uses.
        """
        return self._version

    @version.setter
    def version(self, version):
        version = str(version)
        if version not in ('1.0', '1.1'):
            raise ValueError(
                "pyvo.io.vosi.tables only supports VOSI versions 1.0 and 1.1")
        self._version = version

    @property
    def tableset(self):
        """
        The tableset. Must be a `TableSet` object.
        """
        return self._tableset

    @tableset.setter
    def tableset(self, tableset):
        self._tableset = tableset

    @property
    def table(self):
        """
        The `Table` root element if present.
        """
        return self._table

    @table.setter
    def table(self, table):
        self._table = table

    @property
    def ntables(self):
        """
        The number of tables in the file.
        """
        return self._ntables

    def _set_version(self, iterator, tag, data, config, pos):
        if 'version' not in data:
            config['version'] = self.version
        else:
            config['version'] = self._version = data['version']
            if config['version'] not in ('1.0', '1.1'):
                vo_warn(W15, config=config, pos=pos)

    def parse(self, iterator, config):
        self._tag_mapping.update({
            "tableset": make_add_complexcontent(
                self, "tableset", "tableset", vs.TableSet),
            "table": make_add_complexcontent(self, "table", "table", vs.Table)
        })

        super(TablesFile, self).parse(iterator, config)

        if self.tableset is None and self.table is None:
            vo_raise(E07, config=config, pos=self._pos)

        self._version = config['version']
        if config['version'] not in ('1.0', '1.1'):
            vo_warn(W15, config=config, pos=self._pos)

        if self.table:
            if version_compare(config['version'], '1.1') < 0:
                vo_warn(W16, config=config, pos=self._pos)
            self._ntables = 1
        else:
            self._ntables = sum(
                len(schema.tables) for schema in self.tableset.schemas)

        return self

    def iter_tables(self):
        """
        Iterates over all tables in the VOSITables file in a "flat" way,
        ignoring the schemas.
        """
        if self.table:
            yield self.table
        else:
            for schema in self.tableset.schemas:
                for table in schema.tables:
                    yield table

    def get_first_table(self):
        """
        When you parse table metadata for a single table here is only one table
        in the file, and that's all you need.
        This method returns that first table.
        """
        for table in self.iter_tables():
            return table
        raise IndexError("No table found in VOSITables file.")

    def get_table_by_name(self, name):
        """
        Looks up a table element by the given name.
        """
        for table in self.iter_tables():
            if table.name == name:
                return table
        raise KeyError("No table with name {} found".format(name))


class CapabilitiesFile(Element):
    """
    capabilities element: represents an entire file.
    The keyword arguments correspond to setting members of the same
    name, documented below.
    """
    _element_name = 'capabilities'

    def __init__(self, config=None, pos=None, **kwargs):
        Element.__init__(self, config=config, pos=pos, **kwargs)

        self._tag_mapping.update({
            "capability": make_add_complexcontent(
                self, "capability", "capabilities", vr.Capability)
        })

        self._capabilities = HomogeneousList(vr.Capability)

    def __repr__(self):
        return repr(self.capabilities)

    def __len__(self):
        return len(self.capabilities)

    def __iter__(self):
        return iter(self.capabilities)

    def __reversed__(self):
        return reversed(self.capabilities)

    def __getitem__(self, key):
        return self.capabilities[key]

    def __contains__(self, item):
        return item in self.capabilities

    @property
    def capabilities(self):
        """List of `~pyvo.io.vosi.voresource.Capability` objects"""
        return self._capabilities

    def parse(self, iterator, config):
        for start, tag, data, pos in iterator:
            if start:
                if tag == "xml":
                    pass
                elif tag == "capabilities":
                    break
            else:
                pass # TODO: vo_raise(E07, config=config, pos=pos)

        super(CapabilitiesFile, self).parse(iterator, config)

        return self


class AvailabilityFile(Element):
    """
    availability element: represents an entire file.
    The keyword arguments correspond to setting members of the same
    name, documented below.
    """
    _element_name = 'availability'

    def __init__(self, config=None, pos=None, **kwargs):
        super(AvailabilityFile, self).__init__(config=config, pos=pos, **kwargs)

        self._tag_mapping.update({
            "availability": make_add_complexcontent(
                self, "availability", "availability", av.Availability)
        })

        self._availability = None

    @property
    def availability(self):
        return self._availability

    @availability.setter
    def availability(self, availability):
        self._availability = availability

    def parse(self, iterator, config):
        super(AvailabilityFile, self).parse(iterator, config)
        return self.availability
