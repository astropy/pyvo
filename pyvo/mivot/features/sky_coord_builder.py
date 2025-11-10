# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Utility transforming MIVOT annotation into SkyCoord instances
"""
import numbers
from astropy.coordinates import SkyCoord
from astropy import units as u
from astropy.coordinates import ICRS, Galactic, FK4, FK5
from astropy.time.core import Time
from pyvo.mivot.glossary import SkyCoordMapping
from pyvo.mivot.utils.exceptions import NoMatchingDMTypeError, MappingError


class SkyCoordBuilder:
    '''
    Utility generating SkyCoord instances from MIVOT annotations

    - SkyCoord instances can only be built from model classes containing the minimal
      set of required parameters (a position).
    - In this implementation, only the mango:EpochPosition class is supported since
      it contains the information required to compute the epoch propagation which is a major use-case
    '''

    def __init__(self, mivot_instance):
        '''
        Constructor

        parameters
        -----------
        mivot_instance: dict or MivotInstance
            Python object generated from the MIVOT block as either a Pyhon object or a dict
        '''
        self._mivot_instance_dict = mivot_instance.to_dict()
        self._map_coord_names = None

    def build_sky_coord(self):
        """
        Build a SkyCoord instance from the MivotInstance dictionary.
        The operation requires the dictionary to have ``mango:EpochPosition`` as dmtype.
        This instance can be either the root of the dictionary or it can be one
        of the Mango properties if the root object is a mango:MangoObject instance
        This is a public method which could be extended to support other dmtypes.

        returns
        -------
        SkyCoord
            Instance built by the method

        raises
        ------
        NoMatchingDMTypeError
            if the SkyCoord instance cannot be built.
        """

        if self._mivot_instance_dict and self._mivot_instance_dict["dmtype"] == "mango:MangoObject":
            property_dock = self._mivot_instance_dict["propertyDock"]
            for mango_property in property_dock:
                if mango_property["dmtype"] == "mango:EpochPosition":
                    self._mivot_instance_dict = mango_property
                    return self._build_sky_coord_from_mango()
            raise NoMatchingDMTypeError(
                "No INSTANCE with dmtype='mango:EpochPosition' has been found:"
                " in the property dock of the MangoObject, "
                "cannot build a SkyCoord from annotations")

        elif self._mivot_instance_dict and self._mivot_instance_dict["dmtype"] == "mango:EpochPosition":
            return self._build_sky_coord_from_mango()
        raise NoMatchingDMTypeError(
            "No INSTANCE with dmtype='mango:EpochPosition' has been found:"
            " cannot build a SkyCoord from annotations")

    def _get_time_instance(self, hk_field, besselian=False):
        """
        Format a date expressed in year as [scale]year
        - Exception possibly risen by Astropy are not caught

        parameters
        ----------
        hk_field: dict
            MIVOT instance attribute
        besselian: boolean
            besselian time scale is used if True, otherwise Julian (default)

        returns
        -------
        Time instance or None

        raise
        -----
        MappingError: if the Time instance cannot be built for some reason
        """
        # Process complex type "mango:DateTime
        if hk_field['dmtype'] == "mango:DateTime":
            representation = hk_field['representation']['value']
            timestamp = hk_field['dateTime']['value']
        # Process simple attribute
        else:
            representation = hk_field.get("unit")
            timestamp = hk_field.get("value")

        if not representation or not timestamp:
            raise MappingError(f"Cannot interpret field {hk_field} "
                               f"as a {('besselian' if besselian else 'julian')} timestamp")

        time_instance = self. _build_time_instance(timestamp, representation, besselian)
        if not time_instance:
            raise MappingError(f"Cannot build a Time instance from {hk_field}")

        return time_instance

    def _build_time_instance(self, timestamp, representation, besselian=False):
        """
        Build a Time instance matching the input parameters.
        - Returns None if the parameters do not allow any Time setup
        - Exception possibly risen by Astropy are not caught at this level

        parameters
        ----------
        timestamp: string or number
            The timestamp must comply with the given representation
        representation: string
            year, iso, ... (See MANGO primitive types derived from ivoa:timeStamp)
        besselian: boolean (optional)
            Flag telling to use the besselain calendar. We assume it to only be
            relevant for FK5 frame
        returns
        -------
        Time instance or None
        """
        if representation in ("year", "yr", "y"):
            # it the timestamp is numeric, we infer its format from the besselian flag
            if isinstance(timestamp, numbers.Number):
                return Time(f"{('B' if besselian else 'J')}{timestamp}",
                            format=("byear_str" if besselian else "jyear_str"))
            if besselian:
                if timestamp.startswith("B"):
                    return Time(f"{timestamp}", format="byear_str")
                elif timestamp.startswith("J"):
                    # a besselain year cannot be given as "Jxxxx"
                    return None
                elif timestamp.isnumeric():
                    # we force the string representation not to break the test assertions
                    return Time(f"B{timestamp}", format="byear_str")
            else:
                if timestamp.startswith("J"):
                    return Time(f"{timestamp}", format="jyear_str")
                elif timestamp.startswith("B"):
                    # a julian year cannot be given as "Bxxxx"
                    return None
                elif timestamp.isnumeric():
                    # we force the string representation not to break the test assertions
                    return Time(f"J{timestamp}", format="jyear_str")
            # no case matches
            return None
        # in the following cases, the calendar (B or J) is given by the besselian flag
        # We force to use the  string representation to avoid breaking unit tests.
        elif representation in ("mjd", "jd", "iso"):
            time = Time(f"{timestamp}", format=representation)
            return (Time(time.byear_str) if besselian else time)

        return None

    def _get_space_frame(self):
        """
        Build an astropy space frame instance from the MIVOT annotations.

        - Equinox are supported for FK4/5
        - Reference location is not supported

        returns
        -------
        FK2, FK5, ICRS or Galactic
            Astropy space frame instance
        """
        coo_sys = self._mivot_instance_dict["spaceSys"]["frame"]
        equinox = None
        frame = coo_sys["spaceRefFrame"]["value"].lower()

        if frame == 'fk4':
            self._map_coord_names = SkyCoordMapping.default_params
            if "equinox" in coo_sys:
                equinox = self._get_time_instance(coo_sys["equinox"], True)
                # by FK4 takes obstime=equinox by default
                return FK4(equinox=equinox)
            return FK4()

        if frame == 'fk5':
            self._map_coord_names = SkyCoordMapping.default_params
            if "equinox" in coo_sys:
                equinox = self._get_time_instance(coo_sys["equinox"])
                return FK5(equinox=equinox)
            return FK5()

        if frame == 'galactic':
            self._map_coord_names = SkyCoordMapping.galactic_params
            return Galactic()

        self._map_coord_names = SkyCoordMapping.default_params
        return ICRS()

    def _build_sky_coord_from_mango(self):
        """
        Build a SkyCoord instance from the ``mango:EpochPosition instance``.

        - The epoch (obstime) is meant to be given in year.
        - ICRS frame is taken by default
        - The cos-delta correction is meant to be applied.
          The case ``mango:pmCosDeltApplied = False`` is not supported yet

        returns
        -------
        SkyCoord
            instance built by the method
        """
        kwargs = {}
        kwargs["frame"] = self._get_space_frame()

        for mango_role, skycoord_field in self._map_coord_names.items():
            # ignore not mapped parameters
            if mango_role not in self._mivot_instance_dict:
                continue
            hk_field = self._mivot_instance_dict[mango_role]
            if mango_role == "obsDate":
                besselian = isinstance(kwargs["frame"], FK4)
                fobstime = self._get_time_instance(hk_field,
                                                      besselian=besselian)
                # FK4 class has an obstime attribute which must be set at instanciation time
                if besselian:
                    kwargs["frame"] = FK4(equinox=kwargs["frame"].equinox, obstime=fobstime)
                # This is not the case for any other space frames
                else:
                    kwargs[skycoord_field] = fobstime
            # ignore not set parameters
            elif (hk_value := hk_field["value"]) is not None:
                # Convert the parallax (mango) into a distance
                if skycoord_field == "distance":
                    kwargs[skycoord_field] = (
                        (hk_value * u.Unit(hk_field["unit"])).to(u.parsec, equivalencies=u.parallax()))
                elif "unit" in hk_field and hk_field["unit"]:
                    kwargs[skycoord_field] = hk_value * u.Unit(hk_field["unit"])
                else:
                    kwargs[skycoord_field] = hk_value
        return SkyCoord(**kwargs)
