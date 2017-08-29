# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
This file contains xml element classes as defined in the VODataService standard.

There are different ways of handling the various xml tags.

* Elements with complex content
* Elements with simple content and attributes
* Elements with simple content without attributes

Elements with complex content are parsed with objects inherited from `Element`.

Elements with simple content are parsed with objects inherited from `Element`
defining a `value` property.
"""

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import re

from astropy.extern import six

from astropy.utils.collections import HomogeneousList
from astropy.utils.xml import check as xml_check
from astropy.io.votable.exceptions import vo_raise, vo_warn, warn_or_raise

from .util import (
    make_add_simplecontent, make_add_complexcontent, Element, ValueMixin)
from . import voresource as vr
from .exceptions import (
    W01, W02, W03, W04, W05, W06, W07, W08, W09, W10, W11, W12, W13, W14, W17,
    W18,
    E01, E02, E03, E04, E05, E06)

__all__ = [
    "TableSet", "TableSchema", "ParamHTTP", "Table", "BaseParam", "TableParam",
    "InputParam", "DataType", "SimpleDataType", "TableDataType", "VOTableType",
    "TAPDataType", "TAPType", "FKColumn", "ForeignKey"]

######################################################################
# FACTORY FUNCTIONS
def _convert_boolean(value, default=None):
    return {
        'false': False,
        '0': False,
        'true': True,
        '1': True
    }.get(value, default)
######################################################################
# ATTRIBUTE CHECKERS
def check_anyuri(uri, config=None, pos=None):
    """
    Raises a `~pyvo.io.vosi.tables.exceptions.VOSITablesWarning` if
    *uri* is not a valid URI.
    As defined in RFC 2396.
    """
    if uri is not None and not xml_check.check_anyuri(uri):
        warn_or_raise(W01, W01, uri, config=config, pos=pos)
        return False
    return True

def check_datatype_flag(data, config=None, pos=None):
    """
    Checks if the datatype flag is valid
    """
    if data not in ('indexed', 'primary', 'nullable'):
        warn_or_raise(W04, W04, data, config=config, pos=pos)
        return False
    return True

######################################################################
# ELEMENT CLASSES
class TableSet(Element):
    """
    TableSet element as described in
    http://www.ivoa.net/xml/VODataService/v1.1

    The set of tables hosted by a resource.
    """
    def __init__(self, version="1.1", config=None, pos=None, **kwargs):
        super(TableSet, self).__init__(config, pos, **kwargs)

        self._tag_mapping.update({
            "schema": make_add_complexcontent(
                self, "schema", "schemas", TableSchema)
        })

        self._version = version
        self._schemas = HomogeneousList(TableSchema)

    def __repr__(self):
        return '<TableSet>... {} schemas ...</TableSet>'.format(
            len(self.schemas))

    @property
    def version(self):
        """The version of the standard"""
        return self._version

    @version.setter
    def version(self, version):
        self._config['version'] = version
        self._version = version

    @property
    def schemas(self):
        """
        A list of schemas. Must contain only `Schema` objects.

        A named description of a set of logically related tables.

        The name given by the "name" child element must be unique within this
        TableSet instance.  If there is only one schema in this set and/or
        there's no locally appropriate name to provide, the name can be set to
        "default".

        This aggregation does not need to map to an actual database, catalog, or
        schema, though the publisher may choose to aggregate along such
        designations, or particular service protocol may recommend it.
        """
        return self._schemas

    def parse(self, iterator, config):
        super(TableSet, self).parse(iterator, config)

        if not self.schemas:
            warn_or_raise(W14, W14, config=config, pos=self._pos)

class TableSchema(Element):
    """
    TableSchema element as described in
    http://www.ivoa.net/xml/VODataService/v1.1

    A detailed description of a logically-related set of tables.
    """
    def __init__(self, config=None, pos=None, **kwargs):
        super(TableSchema, self).__init__(config, pos, **kwargs)

        self._tag_mapping.update({
            "name": make_add_simplecontent(self, "name", "name", W05),
            "title": make_add_simplecontent(self, "title", "title", W13),
            "description": make_add_simplecontent(
                self, "description", "description", W06),
            "utype": make_add_simplecontent(self, "utype", "utype", W09),
            "table": make_add_complexcontent(self, "table", "tables", Table)
        })

        self._name = None
        self._title = None
        self._description = None
        self._utype = None

        self._tables = HomogeneousList(Table)

    def __repr__(self):
        return '<TableSchema name="{}">... {} tables ...</TableSchema>'.format(
            self.name, len(self.tables))

    @property
    def name(self):
        """
        A name for the set of tables.

        This is used to uniquely identify the table set among
        several table sets.  If a title is not present, this
        name can be used for display purposes.

        If there is no appropriate logical name associated with
        this set, the name should be explicitly set to
        "default".
        """
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def title(self):
        """
        a descriptive, human-interpretable name for the table set.

        This is used for display purposes.  There is no requirement
        regarding uniqueness.  It is useful when there are
        multiple schemas in the context (e.g. within a
        tableset; otherwise, the resource title could be
        used instead).
        """
        return self._title

    @title.setter
    def title(self, title):
        self._title = title

    @property
    def description(self):
        """
        A free text description of the tableset that should
        explain in general how all of the tables are related.
        """
        return self._description

    @description.setter
    def description(self, description):
        self._description = description

    @property
    def utype(self):
        """
        an identifier for a concept in a data model that
        the data in this schema as a whole represent.

        The format defined in the VOTable standard is strongly
        recommended.
        """
        return self._utype

    @utype.setter
    def utype(self, utype):
        self._utype = utype

    @property
    def tables(self):
        """
        A list of tables in the schema.  Must contain only `Table` objects.

        A description of one of the tables that makes up the set.
        The table names for the table should be unique.
        """
        return self._tables

    def parse(self, iterator, config):
        super(TableSchema, self).parse(iterator, config)

        if not self.name:
            vo_raise(E06, self._element_name, config=config, pos=self._pos)


@vr.Interface.register_xsi_type('vs:ParamHTTP')
class ParamHTTP(vr.Interface):
    """
    ParamHTTP element as described in
    http://www.ivoa.net/xml/VODataService/v1.1

    A service invoked via an HTTP Query (either Get or Post)
    with a set of arguments consisting of keyword name-value pairs.

    Note that the URL for help with this service can be put into
    the Service/ReferenceURL element.
    """
    def __init__(self, config=None, pos=None, **kwargs):
        super(ParamHTTP, self).__init__(config=config, pos=pos, **kwargs)

        self._tag_mapping.update({
            "queryType": make_add_simplecontent(
                self, "queryType", "querytypes"),
            "resultType": make_add_simplecontent(
                self, "resultType", "resulttype", W17)
        })

        self._querytypes = HomogeneousList(six.text_type)
        self._resulttype = None

    @property
    def querytypes(self):
        """
        The type of HTTP request, either GET or POST.

        The service may indicate support for both GET
        and POST by providing 2 queryType elements, one
        with GET and one with POST.
        """
        return self._querytypes

    @property
    def resulttype(self):
        """The MIME type of a document returned in the HTTP response."""
        return self._resulttype

    @resulttype.setter
    def resulttype(self, resulttype):
        self._resulttype = resulttype

    def parse(self, iterator, config):
        super(ParamHTTP, self).parse(iterator, config)

        if len(self.querytypes) > 2:
            warn_or_raise(W18, W18, config=config, pos=self._pos)


class Table(Element):
    """
    Table element as described in
    http://www.ivoa.net/xml/VODataService/v1.1
    """
    def __init__(self, version="1.1", config=None, pos=None, **kwargs):
        super(Table, self).__init__(config, pos, **kwargs)

        self._tag_mapping.update({
            "name": make_add_simplecontent(self, "name", "name", W05),
            "title": make_add_simplecontent(self, "title", "title", W13),
            "description": make_add_simplecontent(
                self, "description", "description", W06),
            "utype": make_add_simplecontent(self, "utype", "utype", W09),
            "column": make_add_complexcontent(
                self, "column", "columns", TableParam),
            "foreignKey": make_add_complexcontent(
                self, "foreignKey", "foreignkeys", ForeignKey)
        })

        self._name = None
        self._title = None
        self._description = None
        self._utype = None
        self._type = kwargs.get("type")
        self._version = version

        self._columns = HomogeneousList(TableParam)
        self._foreignkeys = HomogeneousList(ForeignKey)

    def __repr__(self):
        return '<Table name="{}">... {} columns ...</Table>'.format(
            self.name, len(self.columns))

    @property
    def name(self):
        """
        the fully qualified name of the table.  This name
        should include all catalog or schema prefixes
        needed to sufficiently uniquely distinguish it in a
        query.

        In general, the format of the qualified name may
        depend on the context; however, when the
        table is intended to be queryable via ADQL, then the
        catalog and schema qualifiers are delimited from the
        table name with dots (.).
        """
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def title(self):
        """
        a descriptive, human-interpretable name for the table.

        This is used for display purposes.  There is no requirement
        regarding uniqueness.
        """
        return self._title

    @title.setter
    def title(self, title):
        self._title = title

    @property
    def description(self):
        """
        a free-text description of the table's contents
        """
        return self._description

    @description.setter
    def description(self, description):
        self._description = description

    @property
    def utype(self):
        """
        an identifier for a concept in a data model that
        the data in this table represent.

        The format defined in the VOTable standard is highly
        recommended.
        """
        return self._utype

    @utype.setter
    def utype(self, utype):
        self._utype = utype

    @property
    def type(self):
        """
        a name for the role this table plays.  Recognized
        values include "output", indicating this table is output
        from a query; "base_table", indicating a table
        whose records represent the main subjects of its
        schema; and "view", indicating that the table represents
        a useful combination or subset of other tables.  Other
        values are allowed.
        """
        return self._type

    @type.setter
    def type(self, type_):
        self._type = type_

    @property
    def version(self):
        """The version of the standard"""
        return self._version

    @version.setter
    def version(self, version):
        self._config['version'] = version
        self._version = version

    @property
    def columns(self):
        """
        A list of columns in the table.  Must contain only `Column` objects.

        A description of a table column.
        """
        return self._columns

    @property
    def foreignkeys(self):
        """
        A list of columns in the table.  Must contain only `ForeignKey` objects.

        a description of a foreign keys, one or more columns
        from the current table that can be used to join with
        another table.
        """
        return self._foreignkeys

    def parse(self, iterator, config):
        super(Table, self).parse(iterator, config)

        if not self.name:
            vo_raise(E06, self._element_name, config=config, pos=self._pos)


class BaseParam(Element):
    """
    BaseParam element as described in
    http://www.ivoa.net/xml/VODataService/v1.1

    a description of a parameter that places no restriction on the parameter's
    data type. As the parameter's data type is usually important, schemas
    normally employ a sub-class of this type (e.g. Param), rather than this type
    directly.
    """
    def __init__(self, config=None, pos=None, **kwargs):
        super(BaseParam, self).__init__(config=config, pos=pos, **kwargs)

        self._tag_mapping.update({
            "name": make_add_simplecontent(self, "name", "name", W05),
            "description": make_add_simplecontent(
                self, "description", "description", W06),
            "unit": make_add_simplecontent(self, "unit", "unit", W07),
            "ucd": make_add_simplecontent(self, "ucd", "ucd", W08),
            "utype": make_add_simplecontent(self, "utype", "utype", W09)
        })

        self._name = None
        self._description = None
        self._unit = None
        self._ucd = None
        self._utype = None

    def __repr__(self):
        return '<BaseParam name="{}"/>'.format(self.name)

    @property
    def name(self):
        """the name of the element"""
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def description(self):
        """
        a free-text description of the element's contents
        """
        return self._description

    @description.setter
    def description(self, description):
        self._description = description

    @property
    def unit(self):
        """the unit associated with all values in the element"""
        return self._unit

    @unit.setter
    def unit(self, unit):
        self._unit = unit

    @property
    def ucd(self):
        """
        the name of a unified content descriptor that
        describes the scientific content of the element.

        There are no requirements for compliance with any
        particular UCD standard.  The format of the UCD can
        be used to distinguish between UCD1, UCD1+, and
        SIA-UCD.  See
        http://www.ivoa.net/Documents/latest/UCDlist.html
        for the latest IVOA standard set.
        """
        return self._ucd

    @ucd.setter
    def ucd(self, ucd):
        self._ucd = ucd

    @property
    def utype(self):
        """
        an identifier for a concept in a data model that
        the data in this element represent.

        The format defined in the VOTable standard is highly recommended.
        """
        return self._utype

    @utype.setter
    def utype(self, utype):
        self._utype = utype


class TableParam(BaseParam):
    """
    TableParam element as described in
    http://www.ivoa.net/xml/VODataService/v1.1

    A description of a table parameter having a fixed data type.
    The allowed data type names match those supported by VOTable.
    """
    def __init__(self, std=None, config=None, pos=None, **kwargs):
        super(TableParam, self).__init__(config=config, pos=pos, **kwargs)

        self._tag_mapping.update({
            "dataType": make_add_complexcontent(
                self, "dataType", "datatype", TableDataType),
            "flag": make_add_simplecontent(
                self, "flag", "flags", check_func=check_datatype_flag)
        })

        self._datatype = None
        self._flags = HomogeneousList(six.text_type)
        self._std = _convert_boolean(std)

    @property
    def datatype(self):
        """The type of data contained in the element"""
        return self._datatype

    @datatype.setter
    def datatype(self, datatype):
        if datatype is not None and not isinstance(datatype, TableDataType):
            raise ValueError("datatype must be an TableDataType object")
        self._datatype = datatype

    @property
    def flags(self):
        """
        A list of flags. Must contain only `six.text_type` objects.

        a keyword representing traits of the column. Recognized values include
        "indexed", "primary", and "nullable".
        """
        return self._flags

    @property
    def std(self):
        """
        If true, the meaning and use of this parameter is
        reserved and defined by a standard model.  If false,
        it represents a database-specific parameter
        that effectively extends beyond the standard.  If
        not provided, then the value is unknown.
        """
        return self._std

    @std.setter
    def std(self, std):
        self._std = std

    def parse(self, iterator, config):
        super(TableParam, self).parse(iterator, config)

        if not self.name:
            vo_raise(E06, self._element_name, config=config, pos=self._pos)


class InputParam(BaseParam):
    """
    InputParam element as described in
    http://www.ivoa.net/xml/VODataService/v1.1

    A description of a service or function parameter having a fixed data type.
    """
    def __init__(
            self, use="optional", std="1", config=None, pos=None, **kwargs):
        BaseParam.__init__(self, config, pos, **kwargs)

        self._datatype = None
        self._use = use
        self._std = _convert_boolean(std, True)

    @property
    def datatype(self):
        """The type of data contained in the element"""
        return self._datatype

    @datatype.setter
    def datatype(self, datatype):
        if datatype is not None and not isinstance(datatype, SimpleDataType):
            raise ValueError("datatype must be an SimpleDataType object")
        self._datatype = datatype

    @property
    def use(self):
        """
        An indication of whether this parameter is required to be provided for
        the application or service to work properly.
        Allowed values are "required" and "optional".
        """
        return self._use

    @use.setter
    def use(self, use):
        self._use = use

    @property
    def std(self):
        """
        If true, the meaning and behavior of this parameter is
        reserved and defined by a standard interface.  If
        false, it represents an implementation-specific
        parameter that effectively extends the behavior of the
        service or application.
        """
        return self._std

    @std.setter
    def std(self, std):
        self._std = std

    def parse(self, iterator, config):
        super(InputParam, self).parse(iterator, config)

        if not self.name:
            vo_raise(E06, self._element_name, config=config, pos=self._pos)


class DataType(ValueMixin, Element):
    """
    DataType element as described in
    http://www.ivoa.net/xml/VODataService/v1.1

    A type (in the computer language sense) associated with a parameter with an
    arbitrary name.

    This XML type is used as a parent for defining data types with a restricted
    set of names.
    """
    def __init__(
            self, arraysize="1", delim=" ", extendedType=None,
            extendedSchema=None, config=None, pos=None, **kwargs
    ):
        super(DataType, self).__init__(config=config, pos=pos, **kwargs)

        self._arraysize = arraysize
        self._delim = delim
        self._extendedtype = extendedType
        self._extendedschema = extendedSchema

    def __repr__(self):
        return '<DataType arraysize={}>{}</DataType>'.format(
            self.arraysize, self.value)

    @property
    def arraysize(self):
        """Specifies the size of the dataType"""
        return self._arraysize

    @arraysize.setter
    def arraysize(self, arraysize):
        if all((
                arraysize is not None,
                not re.match(r"^([0-9]+x)*[0-9]*[*]?(s\W)?$", arraysize)
        )):
            vo_raise(E01, arraysize, self._config, self._pos)
        self._arraysize = arraysize

    @property
    def delim(self):
        """
        the string that is used to delimit elements of an array
        value when arraysize is not "1".

        Unless specifically disallowed by the context,
        applications should allow optional spaces to
        appear in an actual data value before and after
        the delimiter (e.g. "1, 5" when delim=",").

        the default is " "; i.e. the values are delimited by spaces.
        """
        return self._delim

    @delim.setter
    def delim(self, delim):
        self._delim = delim

    @property
    def extendedtype(self):
        """
        The data value represented by this type can be
        interpreted as of a custom type identified by
        the value of this attribute.

        If an application does not recognize this
        extendedType, it should attempt to handle value
        assuming the type given by the element's value.
        string is a recommended default type.

        This element may make use of the extendedSchema
        attribute and/or any arbitrary (qualified)
        attribute to refine the identification of the type.
        """

    @extendedtype.setter
    def extendedtype(self, extendedtype):
        self._extendedtype = extendedtype

    @property
    def extendedschema(self):
        """
        An identifier for the schema that the value given
        by the extended attribute is drawn from.

        This attribute is normally ignored if the
        extendedType attribute is not present.
        """
        return self._extendedschema

    @extendedschema.setter
    def extendedschema(self, extendedschema):
        if extendedschema is not None:
            check_anyuri(extendedschema, self._config, self._pos)
        self._extendedschema = extendedschema


class SimpleDataType(DataType):
    """
    SimpleDataType element as described in
    http://www.ivoa.net/xml/VODataService/v1.1

    A data type restricted to a small set of names which is imprecise as to the
    format of the individual values.

    This set is intended for describing simple input parameters to a service or
    function.
    """
    def _value_check(self, value):
        if value is not None:
            valid_values = (
                'integer', 'real', 'complex', 'boolean', 'char', 'string')
            if value not in valid_values:
                vo_warn(W02, value, self._config, self._pos)


class TableDataType(DataType):
    """
    TableDataType element as described in
    http://www.ivoa.net/xml/VODataService/v1.1

    an abstract parent for a class of data types that can be
    used to specify the data type of a table column.

    Subtypes must be decorated with ``register_xsi_type('ns:name')``.
    """
    _xsi_type_mapping = {}

    @classmethod
    def register_xsi_type(cls, typename):
        """Decorator factory for registering subtypes"""
        def register(class_):
            """Decorator for registering subtypes"""
            cls._xsi_type_mapping[typename] = class_
            return class_
        return register

    def __new__(cls, *args, **kwargs):
        if 'xsi:type' not in kwargs:
            pass

        xsi_type = kwargs.get('xsi:type')
        dtype = cls._xsi_type_mapping.get(xsi_type, cls)

        obj = DataType.__new__(dtype)
        obj.__init__(*args, **kwargs)
        return obj


@TableDataType.register_xsi_type('vs:VOTable')
@TableDataType.register_xsi_type('vs:VOTableType')
class VOTableType(TableDataType):
    """
    VOTableType element as described in
    http://www.ivoa.net/xml/VODataService/v1.1
    """
    def _value_check(self, value):
        if value is not None:
            valid_values = (
                'boolean', 'bit', 'unsignedByte', 'short', 'int', 'long',
                'char', 'unicodeChar', 'float', 'double',
                'floatComplex', 'doubleComplex')
            if value not in valid_values:
                vo_warn(W02, value, self._config, self._pos)


class TAPDataType(TableDataType):
    """
    TAPDataType element as described in
    http://www.ivoa.net/xml/VODataService/v1.1

    an abstract parent for the specific data types supported by the
    Table Access Protocol.
    """
    def __init__(self, size=None, config=None, pos=None, **kwargs):
        super(TAPDataType, self).__init__(config=config, pos=pos, **kwargs)

        self._size = size

    @property
    def size(self):
        """
        the length of the fixed-length value.

        This corresponds to the size Column attribute in
        the TAP_SCHEMA and can be used with data types
        that are defined with a length (CHAR, BINARY).
        """
        return self._size

    @size.setter
    def size(self, size):
        if size is not None and int(size) < 0:
            size = 0
            warn_or_raise(W03, W03, config=self._config, pos=self._pos)
        self._size = size


@TableDataType.register_xsi_type('vs:TAP')
@TableDataType.register_xsi_type('vs:TAPType')
class TAPType(TAPDataType):
    """
    TAPType element as described in
    http://www.ivoa.net/xml/VODataService/v1.1

    a data type supported explicitly by the Table Access Protocol (v1.0).
    """
    def _value_check(self, value):
        if value is not None:
            valid_values = (
                'BOOLEAN', 'SMALLINT', 'INTEGER', 'BIGINT', 'REAL', 'DOUBLE',
                'TIMESTAMP', 'CHAR', 'VARCHAR', 'BINARY', 'VARBINARY',
                'POINT', 'REGION', 'CLOB', 'BLOB')
            if value not in valid_values:
                vo_warn(W02, value, self._config, self._pos)


class FKColumn(Element):
    """
    FKColumn element as described in
    http://www.ivoa.net/xml/VODataService/v1.1
    """
    def __init__(self, config=None, pos=None, **kwargs):
        super(FKColumn, self).__init__(config=config, pos=pos, **kwargs)

        self._tag_mapping.update({
            "fromColumn": make_add_simplecontent(
                self, "fromColumn", "fromcolumn", W10),
            "targetColumn": make_add_simplecontent(
                self, "targetColumn", "targetcolumn", W11)
        })

        self._fromcolumn = None
        self._targetcolumn = None

    def __repr__(self):
        return '<FKColumn fromColumn={} targetColumn={}>...</FKColumn>'.format(
            self.fromcolumn, self.targetcolumn)

    @property
    def fromcolumn(self):
        """
        The unqualified name of the column from the current table.
        """
        return self._fromcolumn

    @fromcolumn.setter
    def fromcolumn(self, fromcolumn):
        self._fromcolumn = fromcolumn

    @property
    def targetcolumn(self):
        """
        The unqualified name of the column from the target table.
        """
        return self._targetcolumn

    @targetcolumn.setter
    def targetcolumn(self, targetcolumn):
        self._targetcolumn = targetcolumn

    def parse(self, iterator, config):
        super(FKColumn, self).parse(iterator, config)

        if self.fromcolumn is None:
            vo_raise(E02, config=config, pos=self._pos)
        if self.targetcolumn is None:
            vo_raise(E03, config=config, pos=self._pos)

class ForeignKey(Element):
    """
    ForeignKey element as described in
    http://www.ivoa.net/xml/VODataService/v1.1
    """
    def __init__(self, config=None, pos=None, **kwargs):
        Element.__init__(self, config, pos, **kwargs)

        self._tag_mapping.update({
            "targetTable": make_add_simplecontent(
                self, "targetTable", "targettable", W12),
            "fkColumn": make_add_complexcontent(
                self, "fkColumn", "fkcolumns", FKColumn),
            "description": make_add_simplecontent(
                self, "description", "description", W06),
            "utype": make_add_simplecontent(self, "utype", "utype", W09)
        })

        self._targettable = None
        self._fkcolumns = HomogeneousList(FKColumn)
        self._description = None
        self._utype = None

    def __repr__(self):
        return '<ForeignKey targetTable={}>...</ForeignKey>'.format(
            self.targettable)

    @property
    def targettable(self):
        """
        the fully-qualified name (including catalog and schema, as
        applicable) of the table that can be joined with the
        table containing this foreign key.
        """
        return self._targettable

    @targettable.setter
    def targettable(self, targettable):
        self._targettable = targettable

    @property
    def fkcolumns(self):
        """
        A list of foreign key columns. Must contain only `FKColumn` objects.

        a pair of column names, one from this table and one
        from the target table that should be used to join the
        tables in a query.
        """
        return self._fkcolumns

    @property
    def description(self):
        """
        a free-text description of what this key points to
        and what the relationship means.
        """
        return self._description

    @description.setter
    def description(self, description):
        self._description = description

    @property
    def utype(self):
        """
        an identifier for a concept in a data model that
        the association enabled by this key represents.

        The format defined in the VOTable standard is highly
        recommended.
        """
        return self._utype

    @utype.setter
    def utype(self, utype):
        self._utype = utype

    def parse(self, iterator, config):
        super(ForeignKey, self).parse(iterator, config)

        if not self.targettable:
            vo_raise(E04, config=config, pos=self._pos)
        if not self.fkcolumns:
            vo_raise(E05, config=config, pos=self._pos)
