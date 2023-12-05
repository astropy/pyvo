# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Implementation of the EpochPropagation in the MIVOT class with
astropy.coordinates.sky_coordinate.SkyCoord and
astropy.coordinates.sky_coordinate.SkyCoord.apply_space_motion.
"""
import numpy as np
import re
from astropy import time
from astropy.time import Time
from astropy.coordinates import SkyCoord, frame_transform_graph
import astropy.units as u

from pyvo.mivot.utils.exceptions import UnitException, TimeFormatException, SkyCoordParameterException
from pyvo.mivot.viewer.mivot_class import MivotClass
from pyvo.mivot.utils.vocabulary import MangoRoles, EpochPropagation_fields, regex_patterns, \
    skycoord_param_fk4, skycoord_param_galactic, skycoord_param_default
from pyvo.utils.prototype import prototype_feature


@prototype_feature('MIVOT')
class EpochPropagation:
    """
    This class allows computing the position of a SkyCoord object at a new time dt.
    It offers to build a SkyCoord object from the data row of the MivotClass, and to apply the space motion.
    """
    def __init__(self, row_view):
        """
        Constructor of the EpochPropagation class.
        Contains all Mango attributes needed for computing EpochPropagation.

        Parameters
        ----------
        row_view : ~`pyvo.mivot.viewer.mivot_class.MivotClass`
            The data row as a MivotClass.
        """
        self.longitude = None
        self.longitude_unit = None
        self.latitude = None
        self.latitude_unit = None
        self.pmLongitude = None
        self.pmLongitude_unit = None
        self.pmLatitude = None
        self.pmLatitude_unit = None
        self.radialVelocity = None
        self.radialVelocity_unit = None
        self.parallax = None
        self.parallax_unit = None
        self.epoch = None
        self.equinox = None
        self.frame = None
        self.pmCosDeltApplied = None
        self.reference_system = None
        self._updateEpoch(row_view)
        self._sky_coord = self.sky_coordinates()

    def _updateEpoch(self, mivot_class, type_epoch=False):
        """
        Initialize and update the attributes of the EpochPropagation object.
        For each leaf (ATTRIBUTE), we call the _fill_epoch_propagation function.

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
                        self._updateEpoch(item, True)
                    else:
                        self._updateEpoch(item)

            elif isinstance(value, MivotClass):
                if isinstance(value.__dict__, dict):
                    if 'value' not in value.__dict__:
                        if mivot_class.dmtype == 'EpochPosition' or type_epoch is True:
                            self._updateEpoch(value, True)
                        else:
                            self._updateEpoch(value)

                    elif 'value' in value.__dict__:
                        if mivot_class.dmtype == 'EpochPosition' or type_epoch is True:
                            self._fill_epoch_propagation(mivot_class, key.lower(), value.__dict__)
                        else:
                            self._updateEpoch(value)
                else:
                    self._updateEpoch(value)

    def _fill_epoch_propagation(self, mivot_class, key_low, value):
        """
        Fill the attributes EpochPropagation object. This function is called for each leaf of the MIVOT class.

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
                self.longitude_unit = self._mivot_unit_to_astropy_unit(**value)
            elif "pm" in key_low:
                self.pmLongitude = value['value']
                self.pmLongitude_unit = self._mivot_unit_to_astropy_unit(**value)

        elif key_low.endswith(MangoRoles.LATITUDE) or key_low.endswith("dec"):
            if "pm" not in key_low:
                self.latitude = value['value']
                self.latitude_unit = self._mivot_unit_to_astropy_unit(**value)
            elif "pm" in key_low:
                self.pmLatitude = value['value']
                self.pmLatitude_unit = self._mivot_unit_to_astropy_unit(**value)

        elif key_low.endswith(MangoRoles.RADIAL_VELOCITY.lower()):
            self.radialVelocity = value["value"]
            self.radialVelocity_unit = self._mivot_unit_to_astropy_unit(**value)

        elif key_low.endswith(MangoRoles.PARALLAX):
            self.parallax = value["value"]
            self.parallax_unit = self._mivot_unit_to_astropy_unit(**value)

        elif key_low.endswith(MangoRoles.EPOCH):
            self.epoch = self._mivot_time_to_astropy_time(**value)

        elif key_low.endswith(MangoRoles.EQUINOX):
            self.equinox = self._mivot_time_to_astropy_time(**value)

        elif key_low.endswith(MangoRoles.PMCOSDELTAPPLIED):
            self.pmCosDeltApplied = value["value"]

        elif mivot_class.dmtype == "StdRefLocation":
            self.reference_system = value["value"]

    def _mivot_unit_to_astropy_unit(self, **mivot_class):
        """
        Convert a string unit from MivotClass to an astropy unit.

        Parameters
        ----------
        mivot_class : dict
            The dictionary of the MivotClass.

        Returns
        -------
        ~`astropy.units.Unit`
            The astropy unit.
        """
        if 'astropy_unit' in mivot_class.keys():
            return mivot_class["astropy_unit"]
        else:
            raise UnitException("Can't find the Astropy Unit equivalence for {}".format(mivot_class["value"]))

    def _mivot_time_to_astropy_time(self, **mivot_class):
        """
        Convert a string time from MivotClass to an astropy time.

        Parameters
        ----------
        mivot_class : dict
            The dictionary of the MivotClass.

        Returns
        -------
        ~`astropy.time.Time`
            The astropy time.
        """
        if 'astropy_unit_time' in mivot_class.keys():
            return Time(mivot_class["value"], format=mivot_class["astropy_unit_time"])
        else:
            for format_name, regex_pattern in regex_patterns.items():
                regex = re.compile(regex_pattern)
                match = regex.fullmatch(str(mivot_class["value"]))
                if match:
                    return time.Time(mivot_class["value"], format=format_name)
        raise TimeFormatException("Can't find the Astropy Time equivalence for {}"
                                  .format(mivot_class["value"]))

    def sky_coordinates(self):
        """
        Return a SkyCoord object from the REFERENCE of the XML object.
        Create first a dictionary of arguments to pass to the SkyCoord constructor.
        The names of the arguments depend on the frame.
        """
        kwargs = {}
        map_coord_names = None
        if self.frame == 'fk4':
            map_coord_names = skycoord_param_fk4
        elif self.frame == 'galactic':
            map_coord_names = skycoord_param_galactic
        else:
            map_coord_names = skycoord_param_default

        for elm in EpochPropagation_fields:
            if getattr(self, elm) is not None:
                if elm not in map_coord_names.keys():
                    raise SkyCoordParameterException("The {} attribute is not in the SkyCoord constructor "
                                                     "for the frame {}".format(elm, self.frame))
                elif elm in ('frame', 'epoch', 'equinox'):
                    kwargs[map_coord_names[elm]] = getattr(self, elm)
                elif elm == 'pmLongitude':
                    kwargs[map_coord_names[elm]] = self._apply_cos_delta() * getattr(self, elm + "_unit")
                else:
                    kwargs[map_coord_names[elm]] = getattr(self, elm) * getattr(self, elm + "_unit")

        if self.parallax_unit != u.pc:  # If the parallax is not in parsec, we convert it
            kwargs["distance"] = (self.parallax * self.parallax_unit).to(u.parsec, equivalencies=u.parallax())

        if self.reference_system is not None:
            return SkyCoord(**kwargs).radial_velocity_correction(self.reference_system, self.epoch)

        else:
            return SkyCoord(**kwargs)

    def _apply_cos_delta(self):
        """
        Return the pmLatitude corrected by the cos(delta) factor if it was not applied in the XML object.

        Returns
        -------
        float
            The pmLatitude corrected by the cos(delta) factor.
        """
        if self.pmCosDeltApplied is False:
            if ((self.latitude == 90 and self.latitude_unit == u.degree)
                    or (self.latitude == np.pi / 2 and self.latitude_unit == u.radian)):
                raise ValueError("The cos(delta) factor can't be applied because the declination is 90°.")
            else:
                return self.longitude / np.cos(self.latitude)
        else:
            return self.pmLongitude

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
        return self.pmLongitude

    @ref_pm_long.setter
    def ref_pm_long(self, value):
        self.pmLongitude = value

    @property
    def ref_pm_lat(self):
        return self.pmLatitude

    @ref_pm_lat.setter
    def ref_pm_lat(self, value):
        self.pmLatitude = value
