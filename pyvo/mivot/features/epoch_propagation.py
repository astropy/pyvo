# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Implementation of the EpochPropagation in the MIVOT class with
astropy.coordinates.sky_coordinate.SkyCoord and
astropy.coordinates.sky_coordinate.SkyCoord.apply_space_motion.
"""
from astropy.coordinates import SkyCoord
from astropy.coordinates import frame_transform_graph
import astropy.units as u
from astropy.time import Time

from pyvo.mivot.viewer.mivot_class import MivotClass
from pyvo.mivot.utils.vocabulary import MangoRoles
from pyvo.utils.prototype import prototype_feature


@prototype_feature('MIVOT')
class EpochPropagation:
    """
    This class allows computing the position of a SkyCoord object at a new time dt.
    It builds a SkyCoord object from the data row of the MivotClass, and then applies the space motion.
    """
    fields = ["longitude", "latitude", "pm_longitude", "pm_latitude", "radial_velocity", "parallax"]
    unit_mapping = {
        "deg": u.degree,
        "hourangle": u.hourangle,
        "arcsec": u.arcsec,
        "mas": u.mas,
        "pc": u.pc,
        "km": u.km,
        "m": u.m,
        "mas/year": u.mas / u.yr,
        "km/s": u.km / u.s,
        "year": u.year,
    }

    def __init__(self, row_view):
        """
        Constructor of the EpochPropagation class.

        Parameters
        ----------
        row_view : ~`pyvo.mivot.viewer.mivot_class.MivotClass`
            The data row as a MivotClass.
        """
        self.longitude = None
        self.longitude_unit = None
        self.latitude = None
        self.latitude_unit = None
        self.pm_longitude = None
        self.pm_longitude_unit = None
        self.pm_latitude = None
        self.pm_latitude_unit = None
        self.radial_velocity = None
        self.radial_velocity_unit = None
        self.parallax = None
        self.parallax_unit = None
        self.epoch = None
        self.frame = None
        self.updateEpoch(row_view)
        self._sky_coord = self.sky_coordinates()

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
        if ("frame" in key_low and "string" in value["dmtype"]
                or value["value"] in frame_transform_graph.get_names()):
            self.frame = value["value"].lower()

        elif key_low.endswith(MangoRoles.LONGITUDE) or key_low.endswith("ra"):
            if "pm" not in key_low:
                self.longitude = value['value']
                self.longitude_unit = self.unit_mapping.get(value['unit'], None)
            elif "pm" in key_low and value["unit"] == "mas/year":
                self.pm_longitude = value['value']
                self.pm_longitude_unit = self.unit_mapping.get(value['unit'], None)

        elif key_low.endswith(MangoRoles.LATITUDE) or key_low.endswith("dec"):
            if "pm" not in key_low:
                self.latitude = value['value']
                self.latitude_unit = self.unit_mapping.get(value['unit'], None)
            elif "pm" in key_low:
                self.pm_latitude = value['value']
                self.pm_latitude_unit = self.unit_mapping.get(value['unit'], None)

        elif ("radial" and "velocity") in key_low:
            self.radial_velocity = value["value"]
            self.radial_velocity_unit = self.unit_mapping.get(value['unit'], None)

        elif key_low.endswith(MangoRoles.PARALLAX):
            self.parallax = value["value"]
            self.parallax_unit = self.unit_mapping.get(value['unit'], None)

        elif "epoch" in key_low and value["unit"] == "year":
            self.epoch = Time(value["value"], format="decimalyear")

    def sky_coordinates(self):
        """
        Return a SkyCoord object from the REFERENCE of the XML object.
        Create first a dictionary of arguments to pass to the SkyCoord constructor.
        """
        if self.frame == ('icrs' or 'fk5' or 'fk4'):
            coord_names = {'longitude': 'ra', 'latitude': 'dec', 'parallax': 'distance',
                           'pm_longitude': 'pm_ra_cosdec', 'pm_latitude': 'pm_dec'}

            kwargs = {'frame': self.frame, 'obstime': self.epoch}
            for elm in self.fields:
                if getattr(self, elm) is not None:
                    if elm in coord_names:
                        kwargs[coord_names[elm]] = getattr(self, elm) * getattr(self, elm + "_unit")
                    else:
                        kwargs[elm] = getattr(self, elm) * getattr(self, elm + "_unit")

            if self.parallax_unit == u.mas:
                kwargs["distance"] = (1 / (self.parallax / 1000)) * u.pc

            return SkyCoord(**kwargs)

        elif self.frame == 'galactic':
            coord_names = {'longitude': 'l', 'latitude': 'b', 'parallax': 'distance',
                           'pm_longitude': 'pm_l_cosb', 'pm_latitude': 'pm_b'}

            kwargs = {'frame': self.frame, 'obstime': self.epoch}
            for elm in self.fields:
                if getattr(self, elm) is not None:
                    if elm == coord_names:
                        kwargs[coord_names[elm]] = getattr(self, elm) * getattr(self, elm + "_unit")
                    else:
                        kwargs[elm] = getattr(self, elm) * getattr(self, elm + "_unit")

            return SkyCoord(**kwargs)

    def apply_space_motion(self, dt):
        """
        Return ra and dec of a SkyCoord object by computing the position to a new time dt.

        Parameters
        ----------
        dt : float
            Time in years.
        """
        retour = self.sky_coordinates().apply_space_motion(dt=dt)
        return retour.ra, retour.dec

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
