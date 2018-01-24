# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
SODA classes and mixins
"""
from __future__ import (
    absolute_import, division, print_function, unicode_literals)

from .datalink import DatalinkResults, DatalinkQuery
from .exceptions import DALServiceError

from astropy.units import Quantity, Unit
from astropy.units import spectral as spectral_equivalencies

__all__ = ['SodaRecordMixin', 'SodaQuery']


class SodaRecordMixin(object):
    """
    Mixin for soda functionallity for record classes.
    If used, it's result class must have `pyvo.dal.datalink.AdhocServiceResultsMixin`
    mixed in.
    """
    def _get_soda_resource(self):
        dataformat = self.getdataformat()

        if dataformat is None:
            raise DALServiceError(
                "No dataformat in record. "
                "Maybe you forgot to include it into the TAP Query?")

        if "content=datalink" in dataformat:
            try:
                datalink_result = DatalinkResults.from_result_url(
                    self.getdataurl())

                return datalink_result.get_adhocservice_by_ivoid(
                    b"ivo://ivoa.net/std/SODA#sync")
            except DALServiceError:
                pass

        try:
            return self._results.get_adhocservice_by_ivoid(
                b"ivo://ivoa.net/std/SODA#sync")
        except DALServiceError:
            pass

        # let it count as soda resource
        try:
            return self._results.get_adhocservice_by_ivoid(
                b"ivo://ivoa.net/std/datalink#links")
        except DALServiceError:
            pass

        return None

    def processed(
            self, circle=None, range=None, polygon=None, band=None, **kwargs):
        """
        Iterates over all soda documents in a DALResult.

        Parameters
        ----------
        circle : `astropy.units.Quantity`
            latitude, longitude and radius
        range : `astropy.units.Quantity`
            two longitude + two latitude values describing a rectangle
        polygon : `astropy.units.Quantity`
            multiple (at least three) pairs of longitude and latitude points
        band : `astropy.units.Quantity`
            two bandwidth or frequency values
        """
        soda_resource = self._get_soda_resource()

        if soda_resource:
            soda_query = SodaQuery.from_resource(
                self, soda_resource, circle=circle, range=range,
                polygon=polygon, band=band, **kwargs)

            soda_stream = soda_query.execute_stream()
            soda_query.raise_if_error()
            return soda_stream
        else:
            return self.getdataset()


class SodaQuery(DatalinkQuery):
    """
    a class for preparing a query to a SODA Service.
    """
    def __init__(
            self, baseurl, circle=None, range=None, polygon=None, band=None,
            **kwargs):
        super(SodaQuery, self).__init__(baseurl, **kwargs)

        if circle:
            self.circle = circle

        if range:
            self.range = range

        if polygon:
            self.polygon = polygon

        if band:
            self.band = band

    @property
    def circle(self):
        """
        The CIRCLE parameter defines a spatial region using the circle xtype
        defined in DALI.
        """
        return getattr(self, '_circle', None)

    @circle.setter
    def circle(self, circle):
        setattr(self, '_circle', circle)
        del self.range
        del self.polygon

        if not isinstance(circle, Quantity):
            circle = circle * Unit('deg')
            valerr = ValueError(
                "Circle may be specified using exactly three values")

            try:
                if len(circle) != 3:
                    raise valerr
            except TypeError:
                raise valerr

        self['CIRCLE'] = ' '.join(
            str(value) for value in circle.to(Unit('deg')).value)

    @circle.deleter
    def circle(self):
        if hasattr(self, '_circle'):
            delattr(self, '_circle')
        if 'CIRCLE' in self:
            del self['CIRCLE']

    @property
    def range(self):
        """
        A rectangular range.
        """
        return getattr(self, '_circle', None)

    @range.setter
    def range(self, range):
        setattr(self, '_range', range)
        del self.circle
        del self.polygon

        if not isinstance(range, Quantity):
            range = range * Unit('deg')
            valerr = ValueError(
                "Range may be specified using exactly four values")

            try:
                if len(range) != 4:
                    raise valerr
            except TypeError:
                raise valerr

        self['POS'] = 'RANGE ' + ' '.join(
            str(value) for value in range.to(Unit('deg')).value)

    @range.deleter
    def range(self):
        if hasattr(self, '_range'):
            delattr(self, '_range')
        if 'POS' in self and self['POS'].startswith('RANGE'):
            del self['POS']

    @property
    def polygon(self):
        """
        The POLYGON parameter defines a spatial region using the polygon xtype
        defined in DALI.
        """
        return getattr(self, '_polygon', None)

    @polygon.setter
    def polygon(self, polygon):
        setattr(self, '_polygon', polygon)
        del self.circle
        del self.range

        if not isinstance(polygon, Quantity):
            polygon = polygon * Unit('deg')
            valerr = ValueError(
                "Polygon may be specified using at least three values")

            try:
                if len(polygon) < 3:
                    raise valerr
            except TypeError:
                raise valerr

        self['POLYGON'] = ' '.join(
            str(value) for value in polygon.to(Unit('deg')).value)

    @polygon.deleter
    def polygon(self):
        if hasattr(self, '_polygon'):
            delattr(self, '_polygon')
        if 'POLYGON' in self:
            del self['POLYGON']

    @property
    def band(self):
        """
        The BAND parameter defines the wavelength interval(s) to be extracted
        from the data using a floating point interval
        """
        return getattr(self, "_band", None)

    @band.setter
    def band(self, val):
        setattr(self, "_band", val)

        if not isinstance(val, Quantity):
            # assume meters
            val = val * Unit("meter")
            try:
                if len(val) != 2:
                    raise ValueError(
                        "band must be specified with exactly two values")
            except TypeError:
                raise ValueError(
                    "band must be specified with exactly two values")
        # transform to meters
        val = val.to(Unit("m"), equivalencies=spectral_equivalencies())
        # frequency is counter-proportional to wavelength, so we just sort
        # it to have the right order again
        val.sort()

        self["BAND"] = "{start} {end}".format(
            start=val.value[0], end=val.value[1])

    @band.deleter
    def band(self):
        if hasattr(self, '_band'):
            delattr(self, '_band')
        if 'BAND' in self:
            del self['BAND']
