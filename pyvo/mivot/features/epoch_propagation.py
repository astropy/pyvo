# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Implementation of the EpochPropagation in the MIVOT class with
astropy.coordinates.sky_coordinate.SkyCoord and
astropy.coordinates.sky_coordinate.SkyCoord.apply_space_motion.
"""
from astropy.coordinates import SkyCoord
import astropy.units as u
from pyvo.utils.prototype import prototype_feature


@prototype_feature('MIVOT')
class EpochPropagation:
    """
    This class allows computing the position of a SkyCoord object at a new time dt.
    It builds a SkyCoord object from the data row of the MivotClass, and then applies the space motion.
    """
    fields = ["longitude", "latitude", "pm_longitude", "pm_latitude"]

    def __init__(self, name):
        self.REFERENCE = {}
        self.name = name

    @property
    def ref_long(self):
        return self.REFERENCE.get("longitude")

    @ref_long.setter
    def ref_long(self, value):
        self.REFERENCE["longitude"] = value

    @property
    def ref_lat(self):
        return self.REFERENCE.get("latitude")

    @ref_lat.setter
    def ref_lat(self, value):
        self.REFERENCE["latitude"] = value

    @property
    def ref_pm_long(self):
        return self.REFERENCE.get("pm_longitude")

    @ref_pm_long.setter
    def ref_pm_long(self, value):
        self.REFERENCE["pm_longitude"] = value

    @property
    def ref_pm_lat(self):
        return self.REFERENCE.get("pm_latitude")

    @ref_pm_lat.setter
    def ref_pm_lat(self, value):
        self.REFERENCE["pm_latitude"] = value

    def SkyCoordinate(self):
        """
        Returns a SkyCoord object from the REFERENCE of the XML object.
        """
        if self.REFERENCE["frame"] == ('icrs' or 'fk5' or 'fk4'):
            return SkyCoord(distance=(self.REFERENCE["parallax"] / 4) * u.pc,
                            radial_velocity=self.REFERENCE["radial_velocity"] * u.km / u.s,
                            ra=self.REFERENCE["longitude"] * u.degree,
                            dec=self.REFERENCE["latitude"] * u.degree,
                            pm_ra_cosdec=self.REFERENCE["pm_longitude"] * u.mas / u.yr,
                            pm_dec=self.REFERENCE["pm_latitude"] * u.mas / u.yr,
                            frame=self.REFERENCE["frame"],
                            obstime=self.REFERENCE["epoch"])

        elif self.REFERENCE["frame"] == 'galatic':
            return SkyCoord(distance=self.REFERENCE["parallax"] * u.pc,
                            l=self.REFERENCE["longitude"] * u.degree,
                            b=self.REFERENCE["latitude"] * u.degree,
                            pm_l_cosb=self.REFERENCE["pm_longitude"] * u.mas / u.yr,
                            pm_b=self.REFERENCE["pm_latitude"] * u.mas / u.yr,
                            frame=self.REFERENCE["frame"],
                            obstime=self.REFERENCE["epoch"])

    def apply_space_motion(self, dt):
        """
        Returns ra and dec of a SkyCoord object by computing the position to a new time dt.

        Parameters
        ----------
        dt : float
            Time in years.
        """
        retour = self.SkyCoordinate().apply_space_motion(dt=dt)
        return retour.ra, retour.dec
