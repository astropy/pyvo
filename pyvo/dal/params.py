# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
This file contains functionallity related to VOTABLE Params.
"""
import numpy as np

from astropy.units import Quantity, Unit
from astropy.time import Time

from .exceptions import DALServiceError


def find_param_by_keyword(keyword, params):
    """
    Searches for a specific param by keyword.
    This function will try to look for the keyword as-is first, and then tries
    to find the uppercase'd version of the keyword.
    """
    if keyword in params:
        return params[keyword]

    keyword = keyword.upper()
    if keyword in params:
        return params[keyword]

    raise KeyError('No param named {} defined'.format(keyword))


registry = dict()


def xtype(name):
    def decorate(cls):
        registry[name] = cls
        return cls
    return decorate


class Converter(object):
    """
    Base class for all converters. Each subclass handles the conversion of a
    input value based on a specific xtype.
    """
    @staticmethod
    def unify_value(func):
        def wrapper(self, value):
            return func(self, Quantity(value))
        return wrapper

    @classmethod
    def from_param(cls, param):
        """
        creates a class instance from a Param element.
        """
        if param.xtype in registry:
            cls = registry[param.xtype]

        return cls(
            param.datatype, param.arraysize, param.unit, param.xtype,
            range_=(param.values.min, param.values.max),
            options={option[1] for option in param.values.options}
        )

    def __init__(
        self, datatype, arraysize, unit, xtype, range_=None, options=None
    ):
        self._arraysize = arraysize
        self._unit = unit
        self._xtype = xtype
        self._range = range_
        self._options = options

    def serialize(self, value):
        """
        Serialize for use in DAL Queries
        """
        if np.isscalar(value):
            return str(value)
        elif not np.isscalar(value):
            return " ".join(str(_) for _ in value)


class Number(Converter):
    def __init__(
        self, datatype, arraysize, unit, xtype, range_=None, options=None
    ):
        if datatype not in {'short', 'int', 'long', 'float', 'double'}:
            pass

        super(Number, self).__init__(
            datatype, arraysize, unit, xtype, range_=range_, options=options)

    @Converter.unify_value
    def serialize(self, value):
        """
        Serialize for use in DAL Queries
        """
        if not isinstance(value, Quantity):
            value = Quantity(value)

        if self._unit:
            if not value.unit.to_string():
                value = value * Unit(self._unit)
            else:
                value = value.to(self._unit)

        return super(Number, self).serialize(value.value)


@xtype('timestamp')
class Timestamp(Converter):
    def __init__(
        self, datatype='char', arraysize='*', unit=None,
        xtype='timestamp', range_=None, options=None
    ):
        if datatype != 'char':
            raise DALServiceError('Datatype is not char')

        super(Timestamp, self).__init__(
            datatype, arraysize, unit, xtype, range_=range_, options=options)

    @Converter.unify_value
    def serialize(self, value):
        """
        Serialize time values for use in DAL Queries
        """
        value = Time(value)

        if value.size == 1:
            return value.isot
        else:
            raise DALServiceError('Expecting a scalar time value')


@xtype('interval')
class Interval(Number):
    def __init__(
        self, datatype, arraysize, unit,
        xtype='interval', range_=None, options=None
    ):
        try:
            arraysize = int(arraysize)
            if arraysize % 2:
                raise DALServiceError('Arraysize is not even')
        except ValueError:
            raise DALServiceError('Arraysize is not even')

        super(Interval, self).__init__(
            datatype, arraysize, unit, xtype, range_=range_, options=options)

    @Converter.unify_value
    def serialize(self, value):
        size = np.size(value)
        if size % 2:
            raise DALServiceError('Interval size is not even')

        return super(Interval, self).serialize(value)


@xtype('point')
class Point(Number):
    def __init__(
        self, datatype, arraysize, unit,
        xtype='point', range_=None, options=None
    ):
        try:
            arraysize = int(arraysize)
            if arraysize != 2:
                raise DALServiceError('Point arraysize must be 2')
        except ValueError:
            raise DALServiceError('Point arraysize must be 2')

        super(Point, self).__init__(
            datatype, arraysize, unit, xtype, range_=range_, options=options)

    @Converter.unify_value
    def serialize(self, value):
        size = np.size(value)
        if size != 2:
            raise DALServiceError('Point size must be 2')

        return super(Point, self).serialize(value)


@xtype('circle')
class Circle(Number):
    def __init__(
        self, datatype, arraysize, unit,
        xtype='circle', range_=None, options=None
    ):
        arraysize = int(arraysize)
        if arraysize != 3:
            raise DALServiceError('Circle arraysize must be 3')

        super(Circle, self).__init__(
            datatype, arraysize, unit, xtype, range_=range_, options=options)

    @Converter.unify_value
    def serialize(self, value):
        size = np.size(value)
        if size != 3:
            raise DALServiceError('Circle size must be 3')

        return super(Circle, self).serialize(value)


@xtype('polygon')
class Polygon(Number):
    def __init__(
        self, datatype, arraysize, unit,
        xtype='polygon', range_=None, options=None
    ):
        try:
            arraysize = int(arraysize)
            if arraysize % 3:
                raise DALServiceError('Arraysize is not a multiple of 3')
        except ValueError:
            if arraysize != '*':
                raise DALServiceError('Arraysize is not a multiple of 3')

        super(Polygon, self).__init__(
            datatype, arraysize, unit, xtype, range_=range_, options=options)

    @Converter.unify_value
    def serialize(self, value):
        size = np.size(value)
        try:
            if size % 3:
                raise DALServiceError('Size is not a multiple of 3')
        except ValueError:
                raise DALServiceError('Size is not a multiple of 3')

        return super(Polygon, self).serialize(value)
