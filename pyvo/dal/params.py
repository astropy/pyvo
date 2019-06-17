# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
This file contains functionallity related to VOTABLE Params.
"""
import numpy as np

from astropy.units import Quantity, Unit
from astropy.time import Time
from astropy.io.votable.converters import (
    get_converter as get_votable_converter)

from .exceptions import DALServiceError


NUMERIC_DATATYPES = {'short', 'int', 'long', 'float', 'double'}


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


def unify_value(func):
    """
    Decorator for serialize method to do unit conversion on input value.
    The decorator converts the input value to the unit in the input param.
    """
    def wrapper(self, value):
        if self._param.unit:
            value = Quantity(value)
            if not value.unit.to_string():
                value = value * Unit(self._param.unit)
            else:
                value = value.to(self._param.unit)

        if isinstance(value, Quantity):
            value = value.value

        return func(self, value)

    return wrapper


def get_converter(param):
    if param.xtype in registry:
        return registry[param.xtype](param)

    if param.datatype in NUMERIC_DATATYPES:
        return Number(param)

    return Converter(param)


class Converter:
    """
    Base class for all converters. Each subclass handles the conversion of a
    input value based on a specific xtype.
    """
    def __init__(self, param):
        self._param = param

    def serialize(self, value):
        """
        Serialize for use in DAL Queries
        """
        return str(value)


class Number(Converter):
    def __init__(self, param):
        if param.datatype not in {'short', 'int', 'long', 'float', 'double'}:
            pass

        super().__init__(param)

    @unify_value
    def serialize(self, value):
        """
        Serialize for use in DAL Queries
        """
        return get_votable_converter(self._param).output(
            value, np.zeros_like(value))


@xtype('timestamp')
class Timestamp(Converter):
    def __init__(self, param):
        if param.datatype != 'char':
            raise DALServiceError('Datatype is not char')

        super().__init__(param)

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
    def __init__(self, param):
        try:
            arraysize = int(param.arraysize)
            if arraysize % 2:
                raise DALServiceError('Arraysize is not even')
        except ValueError:
            raise DALServiceError('Arraysize is not even')

        super().__init__(param)

    @unify_value
    def serialize(self, value):
        size = np.size(value)
        if size % 2:
            raise DALServiceError('Interval size is not even')

        return super().serialize(value)


@xtype('point')
class Point(Number):
    def __init__(self, param):
        try:
            arraysize = int(param.arraysize)
            if arraysize != 2:
                raise DALServiceError('Point arraysize must be 2')
        except ValueError:
            raise DALServiceError('Point arraysize must be 2')

        super().__init__(param)

    @unify_value
    def serialize(self, value):
        size = np.size(value)
        if size != 2:
            raise DALServiceError('Point size must be 2')

        return super().serialize(value)


@xtype('circle')
class Circle(Number):
    def __init__(self, param):
        arraysize = int(param.arraysize)
        if arraysize != 3:
            raise DALServiceError('Circle arraysize must be 3')

        super().__init__(param)

    @unify_value
    def serialize(self, value):
        size = np.size(value)
        if size != 3:
            raise DALServiceError('Circle size must be 3')

        return super().serialize(value)


@xtype('polygon')
class Polygon(Number):
    def __init__(self, param):
        try:
            arraysize = int(param.arraysize)
            if arraysize % 3:
                raise DALServiceError('Arraysize is not a multiple of 3')
        except ValueError:
            if param.arraysize != '*':
                raise DALServiceError('Arraysize is not a multiple of 3')

        super().__init__(param)

    @unify_value
    def serialize(self, value):
        size = np.size(value)
        try:
            if size % 3:
                raise DALServiceError('Size is not a multiple of 3')
        except ValueError:
            raise DALServiceError('Size is not a multiple of 3')

        return super().serialize(value)
