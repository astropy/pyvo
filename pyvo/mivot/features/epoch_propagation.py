# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Implementation of the EpochPropagation in the MIVOT class with
astropy.coordinates.sky_coordinate.SkyCoord and
astropy.coordinates.sky_coordinate.SkyCoord.apply_space_motion.
"""
from astropy.coordinates import SkyCoord
import astropy.units as u
from astropy.time import Time

from pyvo.mivot.viewer.mivot_class import MivotClass
from pyvo.utils.prototype import prototype_feature


@prototype_feature('MIVOT')
class EpochPropagation:
    """
    This class allows computing the position of a SkyCoord object at a new time dt.
    It builds a SkyCoord object from the data row of the MivotClass, and then applies the space motion.
    """
    fields = ["longitude", "latitude", "pm_longitude", "pm_latitude"]

    def __init__(self, row_view):
        """
        Constructor of the EpochPropagation class.

        Parameters
        ----------
        row_view : ~`pyvo.mivot.viewer.mivot_class.MivotClass`
            The data row as a MivotClass.
        """
        self.longitude = None
        self.latitude = None
        self.pm_longitude = None
        self.pm_latitude = None
        self.radial_velocity = None
        self.parallax = None
        self.epoch = None
        self.frame = None
        self.updateEpoch(row_view)
        self._sky_coord = self.SkyCoordinate()

    def updateEpoch(self, mivot_class, type_epoch=False):
        """
        Initialize and update the attributes of the EpochPropagation object.

        Parameters
        ----------
        mivot_class : ~`pyvo.mivot.viewer.mivot_class.MivotClass`
            The data row as a MivotClass.
        type_epoch : bool, optional
            If True, it means that the current MivotClass comes from an EpochPosition instance.
            Default is False.
        """
        for key, value in mivot_class.__dict__.items():
            if isinstance(value, list):
                for item in value:
                    if mivot_class.dmtype == 'EpochPosition' or type_epoch is True:
                        self.updateEpoch(item, True)
                    else:
                        self.updateEpoch(item)

            elif isinstance(value, MivotClass):
                if isinstance(value.__dict__, dict):
                    if 'value' not in value.__dict__:
                        if mivot_class.dmtype == 'EpochPosition' or type_epoch is True:
                            self.updateEpoch(value, True)
                        else:
                            self.updateEpoch(value)

                    elif 'value' in value.__dict__:
                        if mivot_class.dmtype == 'EpochPosition' or type_epoch is True:
                            self._fill_epoch_propagation(key.lower(), value.__dict__)
                        else:
                            self.updateEpoch(value)
                else:
                    self.updateEpoch(value)

    def _fill_epoch_propagation(self, key_low, value):
        """
        Fill the attributes EpochPropagation object.

        Parameters
        ----------
        key_low : str
            The key of the dictionary in lowercase.
        value : dict
            The value of the dictionary.
        """
        if "frame" in key_low and "string" in value["dmtype"]:
            self.frame = value["value"].lower()
        if ("longitude" or "ra") in key_low:
            if "pm" not in key_low and value["unit"] == "deg":
                self.longitude = value['value']
            elif "pm" in key_low and value["unit"] == "mas/year":
                self.pm_longitude = value['value']
        if ("latitude" or "dec") in key_low:
            if "pm" not in key_low and value["unit"] == "deg":
                self.latitude = value['value']
            elif "pm" in key_low and value["unit"] == "mas/year":
                self.pm_latitude = value['value']
        if ("radial" or "velocity") in key_low and value["unit"] == "km/s":
            self.radial_velocity = value["value"]
        if "parallax" in key_low and value["unit"] == ("mas" or "pc"):
            self.parallax = value["value"]
        if "epoch" in key_low and value["unit"] == "year":
            self.epoch = Time(value["value"], format="decimalyear")

    @property
    def ref_long(self):
        return self.longitude

    @ref_long.setter
    def ref_long(self, value):
        self.longitude = value

    @property
    def ref_lat(self):
        return self.latitude

    @ref_lat.setter
    def ref_lat(self, value):
        self.latitude = value

    @property
    def ref_pm_long(self):
        return self.pm_longitude

    @ref_pm_long.setter
    def ref_pm_long(self, value):
        self.pm_longitude = value

    @property
    def ref_pm_lat(self):
        return self.pm_latitude

    @ref_pm_lat.setter
    def ref_pm_lat(self, value):
        self.pm_latitude = value

    def SkyCoordinate(self):
        """
        Returns a SkyCoord object from the REFERENCE of the XML object.
        """
        if self.frame == ('icrs' or 'fk5' or 'fk4'):
            return SkyCoord(distance=(self.parallax / 4) * u.pc,
                            radial_velocity=self.radial_velocity * u.km / u.s,
                            ra=self.longitude * u.degree,
                            dec=self.latitude * u.degree,
                            pm_ra_cosdec=self.pm_longitude * u.mas / u.yr,
                            pm_dec=self.pm_latitude * u.mas / u.yr,
                            frame=self.frame,
                            obstime=self.epoch)

        elif self.frame == 'galatic':
            return SkyCoord(distance=self.parallax * u.pc,
                            radial_velocity=self.radial_velocity * u.km / u.s,
                            l=self.longitude * u.degree,
                            b=self.latitude * u.degree,
                            pm_l_cosb=self.pm_longitude * u.mas / u.yr,
                            pm_b=self.pm_latitude * u.mas / u.yr,
                            frame=self.frame,
                            obstime=self.epoch)

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
