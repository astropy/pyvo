"""
``HeaderMapper`` class source
"""
import logging
from pyvo.mivot.glossary import Roles, EpochPositionAutoMapping
from pyvo.mivot.utils.dict_utils import DictUtils


class HeaderMapper:
    """
    This utility class generates dictionaries from header elements of a VOTable.
    These dictionaries are used as input parameters by `pyvo.mivot.writer.InstancesFromModels`
    to create MIVOT instances that are placed in the GLOBALS block or in the TEMPLATES.
    In the current implementation, the following elements can be extracted:

    - COOSYS -> coords:SpaceSys
    - TIMESYS - coords:TimeSys
    - INFO -> mango:QueryOrigin
    - FIELD -> mango:EpochPosition
    """

    def __init__(self, votable):
        """
        Constructor parameters:

        Parameters
        ----------
        votable : astropy.io.votable.tree.VOTableFile
            parsed votable from which INFO element are processed
        """
        self._votable = votable

    def _check_votable_head_element(self, parameter):
        """
        Check that the parameter is a valid value.

        .. note::
            Vizier uses the ``UNKNOWN`` word to tag not set values
        """
        return parameter is not None and parameter != "UNKNOWN"

    def _extract_query_origin(self):
        """
        Create a mapping dictionary from ``INFO`` elements found
        in the VOTable header.
        This dictionary is used to populate the ``mango:QueryOrigin`` attributes

        Returns
        -------
        dict
            Dictionary that is part of the input parameter for
            :py:meth:`pyvo.mivot.writer.InstancesFromModels.add_query_origin`
        """
        mapping = {}
        for info in self._votable.infos:
            if info.name in Roles.QueryOrigin:
                mapping[info.name] = info.value
        return mapping

    def _extract_data_origin(self, resource):
        """
        Create a mapping dictionary from  ``INFO`` elements found
        in the header of the first VOTable resource.
        This dictionary is used to populate the ``mango:QueryOrigin`` part of
        the ``mango:QueryOrigin`` instance.

        Returns
        -------
        dict
            Dictionary that is part of the input parameter for
            :py:meth:`pyvo.mivot.writer.InstancesFromModels.add_query_origin`
        """
        mapping = {}
        article = None
        for info in resource.infos:
            if info.name in Roles.DataOrigin or info.name == "creator":
                if DictUtils.add_array_element(mapping, "dataOrigin"):
                    article = {}
                if info.name != "creator":
                    article[info.name] = info.value
                else:
                    DictUtils.add_array_element(article, "creators")
                    article["creators"].append(info.value)

        for info in resource.infos:
            art_ref = {}

            if info.name in Roles.Article:
                DictUtils.add_array_element(article, "articles")
                art_ref[info.name] = info.value
            if art_ref:
                article["articles"].append(art_ref)

        mapping["dataOrigin"].append(article)
        return mapping

    def extract_origin_mapping(self):
        """
        Create a mapping dictionary from all  VOTable ``INFO`` elements.
        This dictionary is used to build a ``mango:QueryOrigin`` INSTANCE

        - INFO elements located in the VOTable header are used to build the ``mango:QueryOrigin``
          part which scope is the whole VOtable by construction (one query -> one VOTable)
        - INFO elements located in the resource header are used to build the ``mango:DataOrigin``
          part which scope is the data located in this resource.

        Returns
        -------
        dict
            Dictionary that can be used as input parameter for
            :py:meth:`pyvo.mivot.writer.InstancesFromModels.add_query_origin`
        """
        mapping = self._extract_query_origin()
        for resource in self._votable.resources:
            mapping = {**mapping, **self._extract_data_origin(resource)}
        return mapping

    def extract_coosys_mapping(self):
        """
        Create a mapping dictionary for each ``COOSYS`` element found
        in the first VOTable resource.

        Returns
        -------
        [dict]
            Array of dictionaries which items can be used as input parameter for
            :py:meth:`pyvo.mivot.writer.InstancesFromModels.add_simple_space_frame`
        """
        mappings = []
        for resource in self._votable.resources:
            for coordinate_system in resource.coordinate_systems:
                mapping = {}
                if not self._check_votable_head_element(coordinate_system.system):
                    logging.warning(f"Not valid COOSYS found: ignored in MIVOT: {coordinate_system}")
                    continue
                mapping["spaceRefFrame"] = coordinate_system.system
                if self._check_votable_head_element(coordinate_system.equinox):
                    mapping["equinox"] = coordinate_system.equinox
                if self._check_votable_head_element(coordinate_system.epoch):
                    mapping["epoch"] = coordinate_system.epoch
                mappings.append(mapping)
        return mappings

    def extract_timesys_mapping(self):
        """
        Create a mapping dictionary for each ``TIMESYS`` element found
        in the first VOTable resource.

        .. note::
            the ``origin`` attribute is not supported yet

        Returns
        -------
        [dict]
            Array of dictionaries which items can be used as input parameter for
            :py:meth:`pyvo.mivot.writer.InstancesFromModels.add_simple_time_frame`
        """
        mappings = []
        for resource in self._votable.resources:
            for time_system in resource.time_systems:
                mapping = {}
                if not self._check_votable_head_element(time_system.timescale):
                    logging.warning(f"Not valid TIMESYS found: ignored in MIVOT: {time_system}")
                    continue
                mapping["timescale"] = time_system.timescale
                if self._check_votable_head_element(time_system.refposition):
                    mapping["refPosition"] = time_system.refposition
                mappings.append(mapping)
        return mappings

    def extract_epochposition_mapping(self):
        """
        Analyze the FIELD UCD-s to infer a data mapping to the EpochPosition class.
        This mapping covers the 6 parameters with the Epoch and their errors.
        The correlation part is not covered since there is no specific UCD for this.
        The UCD-s accepted for each parameter are defined in `pyvo.mivot.glossary`.

        The error classes are hard-coded as the most likely types.

        - PErrorSym2D for 2D parameters
        - PErrorSym1D for 1D parameters

        Returns
        -------
        (dict, dict)
            A mapping proposal for the EpochPosiion + errors that can be used as input parameter
            by :py:meth:`pyvo.mivot.writer.InstancesFromModels.add_mango_epoch_position`.
        """
        def _check_ucd(mapping_entry, ucd, mapping):
            """
            Inner function checking that mapping_entry matches with ucd according to
            `pyvo.mivot.glossary`
            """
            if mapping_entry in mapping:
                return False
            dict_entry = getattr(EpochPositionAutoMapping, mapping_entry)
            if isinstance(dict_entry, list):
                return ucd in dict_entry
            else:
                return ucd.startswith(dict_entry)

        def _check_obs_date(field):
            """ check if the field can be interpreted as a value date time
            This algorithm is a bit specific for Vizier CS
            """
            xtype = field.xtype
            unit = field.unit
            representation = None
            if xtype == "timestamp" or unit == "'Y:M:D'" or unit == "'Y-M-D'":
                representation = "iso"
            # let's assume that dates expressed as days are MJD
            elif xtype == "mjd" or unit == "d":
                representation = "mjd"

            if representation is None and unit == "year":
                representation = "year"

            if representation is not None:
                field_ref = field.ID if field.ID is not None else field.name
                return {"dateTime": field_ref, "representation": representation}
            return None

        table = self._votable.get_first_table()
        fields = table.fields
        mapping = {}
        error_mapping = {}

        for field in fields:
            ucd = field.ucd
            for mapping_entry in Roles.EpochPosition:
                if _check_ucd(mapping_entry, ucd, mapping) is True:
                    if mapping_entry == "obsDate":
                        if (obs_date_mapping := _check_obs_date(field)) is not None:
                            mapping[mapping_entry] = obs_date_mapping
                    else:
                        mapping[mapping_entry] = field.ID if field.ID is not None else field.name
                    # Once we got a parameter mapping, we look for its associated error
                    # This nested loop makes sure we never have error without value
                    for err_field in fields:
                        err_ucd = err_field.ucd
                        # We assume the error UCDs are the same the these of the
                        # related quantities but prefixed with "stat.error;" and without "meta.main" qualifier
                        if err_ucd == ("stat.error;" + ucd.replace(";meta.main", "")):
                            param_mapping = err_field.ID if err_field.ID is not None else err_field.name
                            if mapping_entry == "parallax":
                                error_mapping[mapping_entry] = {"class": "PErrorSym1D",
                                                                "sigma": param_mapping}
                            elif mapping_entry == "radialVelocity":
                                error_mapping[mapping_entry] = {"class": "PErrorSym1D",
                                                                "sigma": param_mapping}
                            elif mapping_entry == "longitude":
                                if "position" in error_mapping:
                                    error_mapping["position"]["sigma1"] = param_mapping
                                else:
                                    error_mapping["position"] = {"class": "PErrorSym2D",
                                                                 "sigma1": param_mapping}
                            elif mapping_entry == "latitude":
                                if "position" in error_mapping:
                                    error_mapping["position"]["sigma2"] = param_mapping
                                else:
                                    error_mapping["position"] = {"class": "PErrorSym2D",
                                                                 "sigma2": param_mapping}
                            elif mapping_entry == "pmLongitude":
                                if "properMotion" in error_mapping:
                                    error_mapping["properMotion"]["sigma1"] = param_mapping
                                else:
                                    error_mapping["properMotion"] = {"class": "PErrorSym2D",
                                                                     "sigma1": param_mapping}
                            elif mapping_entry == "pmLatitude":
                                if "properMotion" in error_mapping:
                                    error_mapping["properMotion"]["sigma2"] = param_mapping
                                else:
                                    error_mapping["properMotion"] = {"class": "PErrorSym2D",
                                                                     "sigma2": param_mapping}

        return mapping, error_mapping
