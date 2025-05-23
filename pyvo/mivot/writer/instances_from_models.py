'''
Created on 6 Feb 2025

@author: laurentmichel
'''
import logging
import re
import requests
# Use defusedxml only if already present in order to avoid a new dependency.
try:
    from defusedxml import ElementTree as etree
    # Element not implemented in recent versions of defusedxml
    from xml.etree.ElementTree import Element
except ImportError:
    from xml.etree import ElementTree as etree
    from xml.etree.ElementTree import Element
from pyvo.mivot.utils.mivot_utils import MivotUtils
from pyvo.mivot.utils.xml_utils import XmlUtils
from pyvo.mivot.utils.xpath_utils import XPath
from pyvo.mivot.utils.vocabulary import Att, Ele
from pyvo.mivot.utils.exceptions import MappingError
from pyvo.mivot.writer.annotations import MivotAnnotations
from pyvo.mivot.writer.mango_object import MangoObject
from pyvo.mivot.writer.instance import MivotInstance
from pyvo.mivot.writer.header_mapper import HeaderMapper

from pyvo.mivot.glossary import (
    VodmlUrl, IvoaType, ModelPrefix, Url, CoordSystems)


class InstancesFromModels(object):
    """
    **Top-level API class** that allows to create VOTable annotations with objects issued
    from the Mango model and its imported classes.

    The annotation structure is handled by the API based on mapping
    rules provided by the user.

    The classes currently supported are:

    - Photometric Calibrations (PhotDM)
    - Spatial and temporal coordinate systems (Coordinates DM)
    - MangoObject (QueryOrigin, EpochPosition, Brightness and Color)

    The mapping built by this API relates to the first table.
    """

    def __init__(self, votable, *, dmid=None):
        """
        Constructor parameters:

        Parameters
        ----------
        votable : astropy.io.votable.tree.VOTableFile
            parsed votable to be annotated
        dmid : string, optional (default is None)
            Column identifier or value (is starts with ``*``) to be used as identifier of the
            MangoObject mapping each data row
        """
        self._votable = votable
        self._table = votable.get_first_table()
        self._header_mapper = HeaderMapper(self._votable)
        self._mango_instance = MangoObject(self._table, dmid=dmid)
        self._annotation = MivotAnnotations()
        self._annotation.add_model("ivoa",
                                   vodml_url=VodmlUrl.ivoa)

    @property
    def mivot_block(self):
        return self._annotation.mivot_block

    def _check_value_consistency(self, word, suggested_words):
        """
        Utility checking that the word belongs to the list of suggested words
        """
        if word.replace("*", "") not in suggested_words:
            logging.warning("Ref frame %s is not in %s, make sure there is no typo",
                           word, suggested_words)

    def extract_frames(self):
        """
        Build space and time frames (``coords:SpaceSys`` and ``coords:TimeSys``) from
        the INFO elements located in the header of the first VOTable resource.
        The instances are added to the GLOBALS Mivot block.

        .. note::
           The VOTable can host multiple instances of COOSYS or TIMESYS, but in
           the current implementation, only the first one is taken

        Returns
        -------
        {"spaceSys": [{"dmid"}], "timeSys": [{"dmid"}]}
            Dictionary of all dmid-s of the frames actually added to the annotations.
            These dmid-s must be used by instances ATTRIBUTEs to their related frames.
            This dictionary can be used ``frames`` parameter of ``add_mango_epoch_position``
        """
        ids = {"spaceSys": {}, "timeSys": {}}
        # take the first coord system  assuming it the most relevant
        for coosys_mapping in self._header_mapper.extract_coosys_mapping():
            dmid = self.add_simple_space_frame(**coosys_mapping)
            if "dmid" not in ids["spaceSys"]:
                ids["spaceSys"]["dmid"] = dmid
        for timesys_mapping in self._header_mapper.extract_timesys_mapping():
            dmid = self.add_simple_time_frame(**timesys_mapping)
            if "dmid" not in ids["timeSys"]:
                ids["timeSys"]["dmid"] = dmid
        return ids

    def extract_data_origin(self):
        """
        Build a ``mango:QueryOrigin`` from
        the INFO elements located in the VOTable header.
        The instance is added to the GLOBALS Mivot block.

        Returns
        -------
        `MivotInstance`
            The ``mango:QueryOrigin`` Mivot instance
        """
        mapping = self._header_mapper.extract_origin_mapping()
        return self.add_query_origin(mapping)

    def extract_epoch_position_parameters(self):
        """
        Build a dictionary with the 3 parameters required by
        :py:meth:`pyvo.mivot.writer.InstancesFromModels.add_mango_epoch_position`
        (frames, mapping, semantic).

        - frames: references to the frames created from COOSYS/TIMSYS
          (see :py:meth:`pyvo.mivot.writer.InstancesFromModels.extract_frames`
        - mapping: inferred from the FIELD ucd-s
        - semantics: hard-coded

        This method does not add the ``EpochPosition`` property because the
        mapping parameters often need first to be completed (or fixed) by hand.
        This especially true for the correlations that cannot be automatically
        detected in a generic way (no specific UCD)

        .. code-block::

            epoch_position_mapping = builder.extract_epoch_position_parameters()
            builder.add_mango_epoch_position(**epoch_position_mapping)

        Returns
        -------
        {"frames", "mapping", "semantics"}
            Dictionary of mapping elements that can unpacked to feed ``add_mango_epoch_position()``.
        """
        mapping, error_mapping = self._header_mapper.extract_epochposition_mapping()
        mapping["errors"] = error_mapping
        mapping["correlations"] = {}
        semantics = {"description": "6 parameters position",
                     "uri": "https://www.ivoa.net/rdf/uat/2024-06-25/uat.html#astronomical-location",
                     "label": "Astronomical location"}
        frames = self.extract_frames()
        return {"frames": frames, "mapping": mapping, "semantics": semantics}

    def add_photcal(self, filter_name):
        """
        Add to the GLOBALS the requested photometric calibration as defined in PhotDM1.1

        The MIVOT serialization is provided by the SVO Filter Profile Service
        (https://ui.adsabs.harvard.edu/abs/2020sea..confE.182R/abstract)

        It is returned as one block containing the whole PhotCal instance.
        The filter instance is extracted from the PhotCal object, where it is
        replaced with a REFERENCE.
        This makes the filter available as a GLOBALS to objects that need it.

        - The dmid of the PhotCal is ``_photcal_DMID`` where DMID is the formatted
          version of ``filter_name``
          (see `pyvo.mivot.utils.MivotUtils.format_dmid`).
        - The dmid of the PhotFilter is ``_photfilter_DMID`` where DMID is the formatted
          version of ``filter_name``.

        Parameters
        ----------
        filter_name : str
            FPS identifier (SVO Photcal ID) of the request filter

        Returns
        -------
        (str, str)
            dmids of photcal and filter instances

        """
        response = requests.get(Url.FPS + filter_name)
        if (http_code := response.status_code) != 200:
            logging.error("FPS service error: %s", http_code)
            return None, None
        # get the MIVOT serialization of the requested Photcal (as a string)
        # FPS returns bytes but that might change
        fps_reponse = response.content
        try:
            fps_reponse = fps_reponse.decode('utf-8')
        except (UnicodeDecodeError, AttributeError):
            pass

        # basic parsing of the response to check if an error has been returned
        if "<INFO name=\"QUERY_STATUS\" value=\"ERROR\">" in fps_reponse:
            message = re.search(r'<DESCRIPTION>(.*)</DESCRIPTION>', fps_reponse).group(1)
            raise MappingError(f"FPS service error: {message}")

        # set the identifiers that will be used for both PhotCal and PhotFilter
        cal_id = MivotUtils.format_dmid(filter_name)
        photcal_id = f"_photcal_{cal_id}"
        filter_id = f"_photfilter_{cal_id}"
        # skip if the same dmid is already recorded
        if cal_id in self._annotation._dmids:
            logging.warning("An instance with dmid=%s has already been stored in GLOBALS: skip", cal_id)
            return photcal_id, filter_id
        self._annotation._dmids.append(cal_id)

        logging.info("%s PhotCal can be referred with dmref='%s'", cal_id, photcal_id)
        # parse the PhotCal and extract the PhotFilter node
        photcal_block = etree.fromstring(fps_reponse)

        filter_block = XPath.x_path_contains(photcal_block,
                                             ".//" + Ele.INSTANCE,
                                             Att.dmtype,
                                             "Phot:photometryFilter")[0]
        # Tune the Photcal to be placed as a GLOBALS child (no role but an id)
        # and remove the PhotFilter node which will be shifted at the GLOBALS level
        del photcal_block.attrib["dmrole"]
        photcal_block.set("dmid", photcal_id)
        photcal_block.remove(filter_block)

        # Tune the PhotFilter to be placed as GLOBALS child (no role but an id)
        filter_role = filter_block.get("dmrole")
        del filter_block.attrib["dmrole"]
        filter_block.set("dmid", filter_id)

        # Append a REFERENCE on the PhotFilter node to the PhotCal block
        reference = Element("REFERENCE")
        reference.set("dmrole", filter_role)
        reference.set("dmref", filter_id)
        photcal_block.append(reference)

        self._annotation.add_model("ivoa", vodml_url=VodmlUrl.ivoa)
        self._annotation.add_model("Phot", vodml_url=VodmlUrl.Phot)

        # fix some FPS tweaks
        photcal_block_string = XmlUtils.pretty_string(photcal_block, lshift="    ")
        photcal_block_string = photcal_block_string.replace(
            "<ATTRIBUTE dmrole=\"Phot:ZeroPoint.softeningParameter\" dmtype=\"ivoa:real\" value=\"\"/>",
            "<!-- ATTRIBUTE dmrole=\"Phot:ZeroPoint.softeningParameter\""
            " dmtype=\"ivoa:real\" value=\"\"/ -->")
        filter_block_string = XmlUtils.pretty_string(filter_block, lshift="    ")
        filter_block_string = filter_block_string.replace("Phot:photometryFilter", "Phot:PhotometryFilter")
        filter_block_string = filter_block_string.replace("Phot:PhotCal.photometryFilter.bandwidth",
                                                          "Phot:PhotometryFilter.bandwidth")
        self._annotation.add_globals(photcal_block_string)
        self._annotation.add_globals(filter_block_string)

        return photcal_id, filter_id

    def add_simple_space_frame(self, spaceRefFrame="ICRS", refPosition="BARYCENTER",
                               equinox=None, epoch=None):
        """
        Adds a SpaceSys instance to the GLOBALS block as defined in the Coordinates
        data model V1.0 (https://ivoa.net/documents/Coords/20221004/index.html).

        Notes:

        - This function implements only the most commonly used features. Custom reference positions
          for TOPOCENTER frames are not supported. However, methods for implementing the missing
          features can be derived from this code.
        - A warning is emitted if either ``spaceRefFrame`` or ``refPosition``
          have unexpected values.
        - No error is raised if the parameter values are inconsistent.
        - The ``dmid`` of the time frame is built from ``spaceRefFrame``,
          ``refrefPosition_position`` and ``equinox``.

        Parameters
        ----------
        spaceRefFrame : str, optional, default "ICRS"
            The reference frame for the space frame.

        refPosition : str, optional, default "BARYCENTER"
            The reference position for the space frame.

        equinox : str, optional, default None
            The equinox for the reference frame, if applicable.

        epoch : str, optional, default None
            The epoch for the reference location, if applicable.

        Returns
        -------
        str
            The actual dmid of the time frame INSTANCE
        """
        # build the dmid
        dmid = f"_spaceframe_{spaceRefFrame.replace('*', '')}"
        if equinox:
            dmid += f"_{equinox.replace('*', '')}"
        if refPosition:
            dmid += f"_{refPosition.replace('*', '')}"

        # skip if the same dmid is already recorded
        if dmid in self._annotation._dmids:
            logging.warning("A spaceSys instance with dmid=%s has already been stored in GLOBALS: skip",
                            dmid)
            return dmid
        logging.info("spaceSys %s can be referred with dmref='%s'", spaceRefFrame, dmid)
        self._annotation._dmids.append(dmid)
        # add (or overwrite) used models
        self._annotation.add_model(ModelPrefix.ivoa, vodml_url=VodmlUrl.ivoa)
        self._annotation.add_model(ModelPrefix.coords, vodml_url=VodmlUrl.coords)

        # check whether ref_frame and ref_position are set with appropriate values
        self._check_value_consistency(spaceRefFrame, CoordSystems.space_frames)
        self._check_value_consistency(refPosition, CoordSystems.ref_positions)

        # Build the SpaceSys instance component by component
        space_system_instance = MivotInstance(dmtype=f"{ModelPrefix.coords}:SpaceSys",
                                              dmid=dmid)
        # let's start with the space frame
        space_frame_instance = MivotInstance(dmtype=f"{ModelPrefix.coords}:SpaceFrame",
                                             dmrole=f"{ModelPrefix.coords}:PhysicalCoordSys.frame")
        space_frame_instance.add_attribute(dmtype=IvoaType.string,
                                           dmrole=f"{ModelPrefix.coords}:SpaceFrame.spaceRefFrame",
                                           value=MivotUtils.as_literal(spaceRefFrame))
        if equinox is not None:
            space_frame_instance.add_attribute(dmtype=f"{ModelPrefix.coords}:Epoch",
                                               dmrole=f"{ModelPrefix.coords}:SpaceFrame.equinox",
                                               value=MivotUtils.as_literal(equinox))
        # then let's build the reference position.
        # The RefLocation type depends on the presence of an epoch (see coords DM)
        if epoch is not None:
            ref_position_instance = MivotInstance(dmtype=f"{ModelPrefix.coords}:CustomRefLocation",
                                                  dmrole=f"{ModelPrefix.coords}:SpaceFrame.refPosition")
            ref_position_instance.add_attribute(dmtype=IvoaType.string,
                                                dmrole=f"{ModelPrefix.coords}:CustomRefLocation.position",
                                                value=MivotUtils.as_literal(refPosition))
            ref_position_instance.add_attribute(dmtype="coords:Epoch",
                                                dmrole=f"{ModelPrefix.coords}:CustomRefLocation.epoch",
                                                value=MivotUtils.as_literal(epoch))
        else:
            ref_position_instance = MivotInstance(dmtype=f"{ModelPrefix.coords}:StdRefLocation",
                                                  dmrole=f"{ModelPrefix.coords}:SpaceFrame.refPosition")
            ref_position_instance.add_attribute(dmtype=IvoaType.string,
                                                dmrole=f"{ModelPrefix.coords}:StdRefLocation.position",
                                                value=MivotUtils.as_literal(refPosition))
        # and pack everything
        space_frame_instance.add_instance(ref_position_instance)
        space_system_instance.add_instance(space_frame_instance)
        # add the SpaceSys instance to the GLOBALS block
        self._annotation.add_globals(space_system_instance)

        return dmid

    def add_simple_time_frame(self, timescale="TCB", *, refPosition="BARYCENTER"):
        """
        Adds a TimeSys instance to the GLOBALS block as defined in the Coordinates
        data model V1.0 (https://ivoa.net/documents/Coords/20221004/index.html).

        Notes:

        - This function implements only the most commonly used features. *Custom reference directions*
          are not supported. However, methods for implementing missing features can be derived from
          this code.
        - A warning is emitted if either ``timescale`` or ``refPosition`` have unexpected values.
        - No error is raised if the parameter values are inconsistent.
        - The ``dmid`` of the time rame is built from ``timescale`` and ``refPosition``.

        Parameters
        ----------
        timescale : str, optional, default "TCB"
            The reference frame for the time frame.

        refPosition : str, optional, default "BARYCENTER"
            The reference position for the time frame.

        Returns
        -------
        str
            The actual dmid of the time frame INSTANCE
        """
        # buikd the dmid
        dmid = f"_timeframe_{timescale.replace('*', '')}"
        if refPosition:
            dmid += f"_{refPosition.replace('*', '')}"
        dmid = MivotUtils.format_dmid(dmid)
        # skip if the same dmid is already recorded
        if dmid in self._annotation._dmids:
            logging.warning("An timeSys instance with dmid=%s has already been stored in GLOBALS: skip", dmid)
            return dmid
        logging.info("timeSys  %s can be referred with dmref='%s'", timescale, dmid)
        self._annotation._dmids.append(dmid)
        # add (or overwrite) used models
        self._annotation.add_model(ModelPrefix.ivoa, vodml_url=VodmlUrl.ivoa)
        self._annotation.add_model(ModelPrefix.coords, vodml_url=VodmlUrl.coords)
        # check whether ref_frame and ref_position are set with appropriate values
        self._check_value_consistency(timescale, CoordSystems.time_frames)
        self._check_value_consistency(refPosition, CoordSystems.ref_positions)
        # Build the TimeSys instance component by component
        time_sys_instance = MivotInstance(dmtype=f"{ModelPrefix.coords}:TimeSys",
                                          dmid=dmid)
        # Let's start with the time frame
        time_frame_instance = MivotInstance(dmtype=f"{ModelPrefix.coords}:TimeFrame",
                                            dmrole=f"{ModelPrefix.coords}:PhysicalCoordSys.frame")
        time_frame_instance.add_attribute(dmtype=IvoaType.string,
                                          dmrole=f"{ModelPrefix.coords}:TimeFrame.timescale",
                                          value=MivotUtils.as_literal(timescale))
        # Then let's build the reference position
        ref_position_instance = MivotInstance(dmtype=f"{ModelPrefix.coords}:StdRefLocation",
                                              dmrole=f"{ModelPrefix.coords}:TimeFrame.refPosition")
        ref_position_instance.add_attribute(dmtype=IvoaType.string,
                                            dmrole=f"{ModelPrefix.coords}:StdRefLocation.position",
                                            value=MivotUtils.as_literal(refPosition))
        # pack everything
        time_frame_instance.add_instance(ref_position_instance)
        time_sys_instance.add_instance(time_frame_instance)
        # add the TimeSys instance to the GLOBALS block
        self._annotation.add_globals(time_sys_instance)

        return dmid

    def add_mango_brightness(self, *, photcal_id=None, mapping={}, semantics={}):
        """
        Add a Mango ``Brightness`` instance to the current `MangoObject` with the specified
        photometric calibration, using the mapping parameter to associate VOtable data with it.
        This method acts as a front-end for `pyvo.mivot.writer.MangoObject` logic.

        Parameters
        ----------
        photcal_id : string, optional (default is None)
            Filter profile service (http://svo2.cab.inta-csic.es/theory/fps/} identifier
            of the desired photometric calibration. It is made of the filter identifier
            followed by the photometric system (e.g. GAIA/GAIA3.Grvs/AB)
        mapping : dict, optional (default to an empty dictionary ({})
            A dictionary defining the mapping of values. It includes:

            - mapping of the brightness value
            - one separate block for the error specification

        semantics : dict, optional (default to an empty dictionary ({})
            A dictionary specifying semantic details to be added to the Mango property.

        Returns
        -------
        `Property`
            The Mango property

        Notes
        -----
        The mapping example below maps the data of the GaiaD3 table that can be found
        in the test suite. Notice that the (fake) error bounds are given as literalS.

        .. code-block:: python

            photcal_id="GAIA/GAIA3.Grvs/AB"
            mapping={"value": "GRVSmag",
                     "error": { "class": "PErrorAsym1D", "low": 1, "high": 3}
                     }
            semantics={"description": "Grvs magnitude",
                       "uri": "https://www.ivoa.net/rdf/uat/2024-06-25/uat.html#magnitude",
                       "label": "magnitude"}

            builder = InstancesFromModels(votable, dmid="DR3Name")
            builder.add_mango_magnitude(photcal_id=photcal_id, mapping=mapping, semantics=semantics)

        """
        # make sure MANGO is mentioned in <MODELS>
        self._annotation.add_model(ModelPrefix.mango, vodml_url=VodmlUrl.mango)

        # Add the photometric calibration instance in <GLOBALS>
        photcal_id, _ = self.add_photcal(photcal_id)
        # Add the brightness property  to the MANGO instance
        return self._mango_instance.add_brightness_property(photcal_id,
                                                            mapping,
                                                            semantics=semantics)

    def add_mango_color(self, *, filter_ids={}, mapping={}, semantics={}):
        """
        Add a Mango ``Color`` instance to the current `MangoObject` with the specified
        low and high filters, using the mapping parameter to associate VOtable data with it.
        This method acts as a front-end for `pyvo.mivot.writer.MangoObject` logic.

        Parameters
        ----------
        filter_ids : string, optional (default to an empty dictionary {})
            Filter profile service (http://svo2.cab.inta-csic.es/theory/fps/} identifiers
            of the high and low photometric calibrations that contain the desired filters.
            Identifiers are made of the filter identifier
            followed by the photometric system (e.g. GAIA/GAIA3.Grvs/AB).
        mapping : dict, optional (default to an empty dictionary ({})
            A dictionary defining the mapping of values. It includes:

            - The mapping of the color value and the color definition (ColorIndex or
              HardnessRatio).
            - One separate block for the error specification.

        semantics : dict, optional (default to an empty dictionary {})
            A dictionary specifying semantic details to be added to the Mango property.

        Returns
        -------
        `Property`
            The Mango property

        Notes
        -----
        The mapping example below maps the data of the GaiaD3 table that can be found
        in the test suite.
        The (fake) color value is given as a literal, it does not refer to any table column.

        .. code-block:: python

            filter_ids={"low": "GAIA/GAIA3.Grp/AB", "high": "GAIA/GAIA3.Grvs/AB"}
            mapping={"value": 0.08, "definition": "ColorIndex",
                     "error": { "class": "PErrorAsym1D", "low": 0.01, "high": 0.02}
                     }
            semantics={"description": "Fake color index",
                       "uri": "http://astrothesaurus.org/uat/1553",
                       "label": "Spectral index"}
            builder = InstancesFromModels(votable, dmid="DR3Name")
            builder.add_mango_color(filter_ids=filter_ids, mapping=mapping, semantics=semantics)

        """
        self._annotation.add_model(ModelPrefix.mango, vodml_url=VodmlUrl.mango)

        filter_low_name = filter_ids["low"]
        filter_high_name = filter_ids["high"]
        _, filter_low_id = self.add_photcal(filter_low_name)
        _, filter_high_id = self.add_photcal(filter_high_name)
        return self._mango_instance.add_color_instance(filter_low_id,
                                                       filter_high_id,
                                                       mapping,
                                                       semantics=semantics)

    def add_mango_epoch_position(self, *, frames={}, mapping={}, semantics={}):
        """
        Add a Mango ``EpochPosition`` instance to the current `MangoObject` with the specified
        frames and semantics, using the mapping parameter to associate VOtable data with it.
        This method acts as a front-end for `pyvo.mivot.writer.MangoObject` logic.

        Parameters
        ----------
        frames : dict, optional (default to an empty dictionary {})
            A dictionary specifying the frames (space and time coordinate systems) to be used.
            Frames parameters are global, they cannot refer to table columns.
            If a frame description contains the "dmid" key, that value will be used as an identifier
            an already installed frame (e.g. with ``extract_frames()``). Otherwise the content of
            the frame description is meant to be used in input parameter
            for ``add_simple_(space)time_frame()``
        mapping : dict, optional (default to an empty dictionary {})
            A dictionary defining the mapping of values. It includes:

            - A flat list for position parameters.
            - Two separate blocks for correlations and error specifications.

        semantics : dict, optional (default to an empty dictionary {})
            A dictionary specifying semantic details to be added to the Mango property.

        Returns
        -------
        `Property`
            The Mango property

        Notes
        -----
        The mapping example below maps the data of the GaiaD3 table that can be found in the test suite.

        .. code-block:: python

            frames={"spaceSys": {"spaceRefFrame": "ICRS", "refPosition": 'BARYCENTER', "equinox": None},
                    "timeSys": {"timescale": "TCB", "refPosition": 'BARYCENTER'}}
            mapping={"longitude": "_RAJ2000", "latitude": "_DEJ2000",
                     "pmLongitude": "pmRA", "pmLatitude": "pmDE",
                     "parallax": "Plx", "radialVelocity": "RV",
                     "correlations": {"isCovariance": True, "longitudeLatitude": "RADEcor",
                                      "latitudePmLongitude": "DEpmRAcor", "latitudePmLatitude": "DEpmDEcor",
                                      "longitudePmLongitude": "RApmRAcor", "longitudePmLatitude": "RApmDEcor",
                                      "longitudeParallax": "RAPlxcor", "latitudeParallax": "DEPlxcor",
                                      "pmLongitudeParallax": "PlxpmRAcor", "pmLatitudeParallax": "PlxpmDEcor",
                     },
                     "errors": { "position": { "class": "PErrorSym2D", "sigma1": "e_RA_ICRS",
                                               "sigma2": "e_DE_ICRS"},
                                 "properMotion": { "class": "PErrorSym2D", "sigma1": "e_pmRA",
                                                   "sigma2": "e_pmDE"},
                                 "parallax": { "class": "PErrorSym1D", "sigma": "e_Plx"},
                                 "radialVelocity": { "class": "PErrorSym1D", "sigma": "e_RV"}
                     }
            }
            semantics={"description": "6 parameters position",
                       "uri": "https://www.ivoa.net/rdf/uat/2024-06-25/uat.html#astronomical-location",
                       "label": "Astronomical location"}

            builder = InstancesFromModels(votable, dmid="DR3Name")
            builder.add_mango_epoch_position(frames=frames, mapping=mapping, semantics=semantics)

        """
        self._annotation.add_model(ModelPrefix.mango, vodml_url=VodmlUrl.mango)

        space_frame_id = ""
        if "spaceSys" in frames and frames["spaceSys"]:
            if "dmid" in frames["spaceSys"]:
                space_frame_id = frames["spaceSys"]["dmid"]
            else:
                space_frame_id = self.add_simple_space_frame(*frames["spaceSys"])
        time_frame_id = ""
        if "timeSys" in frames and frames["timeSys"]:
            if "dmid" in frames["timeSys"]:
                time_frame_id = frames["timeSys"]["dmid"]
            else:
                time_frame_id = self.add_simple_time_frame(**frames["timeSys"])
        return self._mango_instance.add_epoch_position(space_frame_id, time_frame_id, mapping,
                                                       semantics)

    def add_query_origin(self, mapping={}):
        """
        Add the Mango ``QueryOrigin`` instance to the current `MangoObject`.
        This method acts as a front-end for `pyvo.mivot.writer.MangoObject` logic.

        Parameters
        ----------
        mapping : dict, optional (default to an empty dictionary {})
            A dictionary defining the QueryOrigin fields. Mapped fields are global,
            they cannot refer to table columns

        Returns
        -------
        `MivotInstance`

        Notes
        -----
        The partial mapping example below maps a fake QueryOrigin. A complete (long) example based on GaiaD3
        can be found in the test suite.

        .. code-block:: python

            builder = InstancesFromModels(votable, dmid="DR3Name")
            builder.add_query_origin(
                {
                    "service_protocol": "ivo://ivoa.net/std/ConeSearch/v1.03",
                    "request_date": "2025-04-07T12:06:32",
                    "request": (
                        "https://cdsarc.cds.unistra.fr/beta/viz-bin/mivotconesearch"
                        "/I/329/urat1?RA=52.26708&DEC=59.94027&SR=0.05"
                    ),
                    "contact": "cds-question@unistra.fr",
                    "server_software": "7.4.6",
                    "publisher": "CDS",
                    "dataOrigin": [
                        {
                            "ivoid": "ivo://cds.vizier/i/329",
                            "creators": ["Zacharias N."],
                            "cites": "bibcode:2015AJ....150..101Z",
                            "original_date": "2015",
                            "reference_url": "https://cdsarc.cds.unistra.fr/viz-bin/cat/I/329",
                            "rights_uri": "https://cds.unistra.fr/vizier-org/licences_vizier.html",
                            "articles": [{"editor": "Astronomical Journal (AAS)"}],
                        }
                    ],
                }
            )

        """
        self._annotation.add_model(ModelPrefix.mango, vodml_url=VodmlUrl.mango)
        query_origin_instance = MivotInstance(dmtype=f"{ModelPrefix.mango}:origin.QueryOrigin",
                                              dmid="_origin")
        MivotUtils.populate_instance(query_origin_instance, "QueryOrigin", mapping, self._table,
                                     IvoaType.string, as_literals=True, package="origin")
        if "dataOrigin" in mapping:
            origins = []
            data_origin_mappings = mapping["dataOrigin"]
            for data_origin_mapping in data_origin_mappings:
                data_origin_instance = MivotInstance(dmtype=f"{ModelPrefix.mango}:origin.DataOrigin")
                MivotUtils.populate_instance(data_origin_instance, "DataOrigin",
                                             data_origin_mapping, self._table,
                                             IvoaType.string, as_literals=True, package="origin")
                if "articles" in data_origin_mapping:
                    articles = []
                    for art_mapping in data_origin_mapping["articles"]:
                        art_instance = MivotInstance(dmtype=f"{ModelPrefix.mango}:origin.Article")
                        MivotUtils.populate_instance(art_instance, "Article", art_mapping,
                                                     self._table, IvoaType.string,
                                                     as_literals=True, package="origin")
                        articles.append(art_instance)
                    data_origin_instance.add_collection(f"{ModelPrefix.mango}:origin.DataOrigin.articles",
                                                        articles)
                if "creators" in data_origin_mapping:
                    creators = []
                    for art_mapping in data_origin_mapping["creators"]:
                        creators.append(f"<ATTRIBUTE dmtype=\"ivoa:string\" value=\"{art_mapping}\" />")
                    data_origin_instance.add_collection(f"{ModelPrefix.mango}:origin.DataOrigin.creators",
                                                        creators)

                origins.append(data_origin_instance)

            query_origin_instance.add_collection(f"{ModelPrefix.mango}:origin.QueryOrigin.dataOrigin",
                                                 origins)
        self._annotation.add_globals(query_origin_instance)
        self._annotation._dmids.append("_origin")
        return query_origin_instance

    def pack_into_votable(self, *, report_msg="", sparse=False):
        """
        Pack all mapped objects in the annotation block and put it in the VOTable.

        Parameters
        ----------
        report_msg: string, optional (default to an empty string)
            Content of the REPORT Mivot tag
        sparse: boolean, optional (default to False)
            If True, all properties are added in a independent way to the the TEMPLATES.
            They are packed in a MangoObject otherwise.
        """
        self._annotation.set_report(True, report_msg)
        if sparse is True:
            for prop in self._mango_instance.mango_properties:
                # Add each individual property to the TEMPLATES block
                self._annotation.add_templates(prop.xml_string())
        else:
            # Pack the MangoObject and put it in the TEMPLATES
            self._annotation.add_templates(self._mango_instance.get_mango_object(
                with_origin=("_origin" in self._annotation._dmids)))

        self._annotation.build_mivot_block()
        self._annotation.insert_into_votable(self._votable, override=True)
