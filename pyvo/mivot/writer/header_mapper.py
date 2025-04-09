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
    to create MIVOT instances that are placed in the GLOBALS block.
    In the current implementations, the following elements can be extracted:

    - COOSYS -> coords:SpaceSys
    - TIMESYS - coords:TimeSys
    - INFO -> mango:queryOrigin
    """

    def __init__(self, votable):
        """
        Constructor parameters:

        Parameters
        ----------
        votable: astropy.io.votable.tree.VOTableFile
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
        Create a mapping dictionary from  ``INFO`` elements found
        in the VOTable header.
        This dictionary is used to populate the `mango:QueryOrigin` attributes

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
        Create a mapping dictionary from all  ``INFO`` elements found
        in the first VOTable. This dictionary is used to build a `mango:QueryOrigin` INSTANCE

        - INFO elements located in the VOTable header are used to build the ``mango:QueryOrigin``
          part which scope is the whole VOtable by construction (one query -> one VOTable)
        - INFO elements located in the resource header are used to build the `mango:DataOrigin`
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
                    logging.warning("Invalid COOSYS: ignored in MIVOT")

                mapping["spaceRefFrame"] = coordinate_system.system
                if self._check_votable_head_element(coordinate_system.equinox):
                    mapping["equinox"] = coordinate_system.equinox
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
                    logging.warning("Invalid TIMESYS: ignored in MIVOT")
                    return mapping
                mapping["timescale"] = time_system.timescale
                if self._check_votable_head_element(time_system.refposition):
                    mapping["refPosition"] = time_system.refposition
                mappings.append(mapping)

        return mappings
    
    def _check_ucd(self, mapping_entry, ucd, mapping):
        if mapping_entry in mapping:
            return False
        dict_entry = getattr(EpochPositionAutoMapping, mapping_entry)
        if isinstance(dict_entry, list):
            return ucd in dict_entry
        else:
            return ucd.startswith(dict_entry)
    def XXX(self):
        table = self._votable.get_first_table()
        fields = table.fields
        mapping = {}
        error_mapping = {}
        
        for field in fields:
            ucd = field.ucd
            print(field.ucd)
            for mapping_entry in Roles.EpochPosition:
                if self._check_ucd(mapping_entry, ucd, mapping) is True:
                    mapping[mapping_entry] = field.ID if field.ID is not None else field.name
                    for err_field in fields:
                        err_ucd = err_field.ucd
                        if err_ucd == ("stat.error;" + ucd):
                            error_mapping[mapping_entry] = err_field.ID if err_field.ID is not None else err_field.name


        print(mapping)            
        print(error_mapping)            
        """
            {"longitude": "_RAJ2000", "latitude": "_DEJ2000",
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
    
        """
