# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Utility transforming MIVOT annotation into SKYCoord instances
"""

from astropy.coordinates import SkyCoord
from astropy import units as u
from astropy.coordinates import ICRS, Galactic, FK4, FK5


class MangoRoles:
    """
    Place holder for the roles of the mango:EpochPosition roles
    """
    LONGITUDE = "longitude"
    LATITUDE = "latitude"
    PM_LONGITUDE = "pmLongitude"
    PM_LATITUDE = "pmLatitude"
    PARALLAX = "parallax"
    RADIAL_VELOCITY = "radialVelocity"
    EPOCH = "epoch"
    FRAME = "frame"
    EQUINOX = "equinox"
    PMCOSDELTAPPLIED = "pmCosDeltApplied"


# Mapping of the MANGO parameters on the SkyCoord parameters
skycoord_param_default = {
    MangoRoles.LONGITUDE: 'ra', MangoRoles.LATITUDE: 'dec', MangoRoles.PARALLAX: 'distance',
    MangoRoles.PM_LONGITUDE: 'pm_ra_cosdec', MangoRoles.PM_LATITUDE: 'pm_dec',
    MangoRoles.RADIAL_VELOCITY: 'radial_velocity', MangoRoles.EPOCH: 'obstime'}

skycoord_param_galactic = {
    MangoRoles.LONGITUDE: 'l', MangoRoles.LATITUDE: 'b', MangoRoles.PARALLAX: 'distance',
    MangoRoles.PM_LONGITUDE: 'pm_l_cosb', MangoRoles.PM_LATITUDE: 'pm_b',
    MangoRoles.RADIAL_VELOCITY: 'radial_velocity', MangoRoles.EPOCH: 'obstime'}


class SkyCoordBuilder(object):
    '''
    Utility generating SkyCoord instances from MIVOT annotations

    - SkyCoord instances can only be built from model classes containing the minimal
    set of required parameters (a position).
    - In this implementation, only the mango:EpochPosition class is supported since
      it contains the information required to compute the epoch propagation which is a major use-case
    '''

    def __init__(self, mivot_instance_dict):
        '''
        Constructor

        parameters
        -----------
        - mivot_instance_dict: viewer.MivotInstance.to_dict()
                               Internal dictionary of the dynamic Python object generated
                               from the MIVOT block
        '''
        self._mivot_instance_dict = mivot_instance_dict
        self._map_coord_names = None

    def build_sky_coord(self):
        """
        Build a SkyCoord instance from the dynamic Python object attribute.

        returns
        -------
        - SkyCoord instance or None
        """
        if self._mivot_instance_dict and self._mivot_instance_dict["dmtype"] == "mango:EpochPosition":
            return self._build_sky_coord_from_mango()

    def _set_year_time_format(self, hk_field, besselian=False):
        """
        Format a date expressed in year as J-year

        parameters
        ----------
        - hk_field: MIVOT instance parameter as a dict

        returns
        -------
        - formatted string
        """
        scale = "J" if not besselian else "B"
        return (f"{scale}{hk_field['value']}" if hk_field["unit"] in ("yr", "year")
                else hk_field["value"])

    def _get_space_frame(self, obstime=None):
        """
        Build an astropy space frame instance from the MIVOT annotations.

        - Equinox are supported fot FK4/5
        - Ref location are not supported

        parameters
        ----------
        - obstime: string
                   Observation time is given here because KF4 set an default value
                   if it is not given
        returns
        -------
        - Astropy space frame
        """
        coo_sys = self._mivot_instance_dict["coordSys"]
        equinox = None
        frame = coo_sys["spaceRefFrame"]["value"].lower()

        if frame == 'fk4':
            self._map_coord_names = skycoord_param_default
            if "equinox" in coo_sys:
                equinox = self._set_year_time_format(coo_sys["equinox"], True)
                return FK4(equinox=equinox, obstime=obstime)
            return FK4()

        if frame == 'fk5':
            self._map_coord_names = skycoord_param_default
            if "equinox" in coo_sys:
                equinox = self._set_year_time_format(coo_sys["equinox"])
                return FK5(equinox=equinox)
            return FK5()

        if frame == 'galactic':
            self._map_coord_names = skycoord_param_galactic
            return Galactic()

        self._map_coord_names = skycoord_param_default
        return ICRS()

    def _build_sky_coord_from_mango(self):
        """
        Build silently a SkyCoord instance from the mango:EpochPosition instance.
        No error is trapped, unconsistencies in the mango:EpochPosition instance will
        raise Astropy errors.

        - The epoch (obstime) is meant to be given as J-year.
        - ICRS frame is taken by default
        - The cos-delta correction is meant to be applied.
          The case mango:pmCosDeltApplied = False is not suppored yet

        returns
        -------
        - SkyCoord instance
        """
        kwargs = {}
        kwargs["frame"] = self._get_space_frame()

        for key, value in self._map_coord_names.items():
            # ignore not set parameters
            if key not in self._mivot_instance_dict:
                continue
            hk_field = self._mivot_instance_dict[key]
            # format the observation time (J-year by default)
            if value == "obstime":
                # obstime must be set into the KK4 frame but not as an input parameter
                fobstime = self._set_year_time_format(hk_field)
                if isinstance(kwargs["frame"], FK4):
                    kwargs["frame"] = self._get_space_frame(obstime=fobstime)
                else:
                    kwargs[value] = fobstime
            # Convert the parallax (mango) into a distance
            elif value == "distance":
                kwargs[value] = (hk_field["value"]
                                 * u.Unit(hk_field["unit"]).to(u.parsec, equivalencies=u.parallax()))
                kwargs[value] = kwargs[value] * u.parsec
            elif "unit" in hk_field and hk_field["unit"]:
                kwargs[value] = hk_field["value"] * u.Unit(hk_field["unit"])
            else:
                kwargs[value] = hk_field["value"]
        return SkyCoord(**kwargs)
