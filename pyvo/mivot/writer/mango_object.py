'''
Created on 22 Jan 2025

@author: laurentmichel
'''
from pyvo.mivot.utils.exceptions import MappingError
from pyvo.mivot.utils.mivot_utils import MivotUtils
from pyvo.mivot.writer.instance import MivotInstance
from pyvo.mivot.glossary import (
    IvoaType, ModelPrefix, Roles, CoordSystems)


class Property(MivotInstance):
    """
    Class representing one property of a MangoInstance. MangoInstance property
    instances are `pyvo.mivot.writer.MivotInstance` augmented with a semantics block.
    """
    def __init__(self, dmtype=None, *, dmrole=None, dmid=None, semantics={}):
        """
        Parameters
        ----------
        dmtype : str
            dmtype of the INSTANCE (mandatory)
        dmrole : str, optional  (default as None)
            dmrole of the INSTANCE
        dmid : str, optional  (default as None)
            dmid of the INSTANCE
        semantics : dict, optional  (default as {})
            Mapping of the semantic block (supported key: descripton, uri, label)

        Raises
        ------
        MappingError
            If ``dmtype`` is not provided
        """
        super().__init__(dmtype, dmrole=dmrole, dmid=dmid)
        if "description" in semantics:
            # we assume the description as always being a literal
            self.add_attribute(dmtype="ivoa:string",
                               dmrole="mango:Property.description",
                               value=f"*{semantics['description']}")
        if "uri" in semantics or "label" in semantics:
            semantics_instance = MivotInstance(dmtype="mango:VocabularyTerm",
                                               dmrole="mango:Property.semantics")
            if "uri" in semantics:
                semantics_instance.add_attribute(dmtype="ivoa:string",
                                                 dmrole="mango:VocabularyTerm.uri",
                                                 value=f"*{semantics['uri']}")
            if "label" in semantics:
                semantics_instance.add_attribute(dmtype="ivoa:string", dmrole="mango:VocabularyTerm.label",
                                                 value=f"*{semantics['label']}")
            self.add_instance(semantics_instance)


class MangoObject(object):
    """
    This class handles all the components of a MangoObject (properties, origin, instance identifier).
     It is meant to be used by `pyvo.mivot.writer.InstancesFromModels` but not by end users.

    - There is one specific method for each supported property (EpochPosition, photometry and QueryOrigin).
    - The internal structure of the classes is hard-coded in the class logic.

    """

    def __init__(self, table, *, dmid=None):
        '''
        Constructor parameters:

        parameters
        ----------
        table : astropy.io.votable.tree.TableElement
            VOTable table which data is mapped on Mango
        dmid: stringn optional (default as None)
            Reference of the column to be used as a MangoObject identifier
        '''
        self._table = table
        self._properties = []
        self._dmid = dmid

    def _get_error_instance(self, class_name, dmrole, mapping):
        """
        Private method building and returning an Mango error instance

        Returns: MivotInstance
        """
        prop_err_instance = MivotInstance(dmtype=f"{ModelPrefix.mango}:error.{class_name}",
                                          dmrole=dmrole)
        MivotUtils.populate_instance(prop_err_instance, class_name, mapping,
                                     self._table, IvoaType.RealQuantity, package="error")
        return prop_err_instance

    def _add_epoch_position_correlations(self, **correlations):
        """
        Private method building and returning the correlation block of the EpocPosition object.

        Returns
        -------
        `Property`
            The EpochPosition correlations component
        """
        epc_instance = MivotInstance(dmtype=f"{ModelPrefix.mango}:EpochPositionCorrelations",
                                     dmrole=f"{ModelPrefix.mango}:EpochPosition.correlations")

        MivotUtils.populate_instance(epc_instance, "EpochPositionCorrelations",
                                     correlations, self._table, IvoaType.real)
        return epc_instance

    def _add_epoch_position_errors(self, **errors):
        """
        Private method building and returning the error block of the EpocPosition object.

        Returns
        -------
        `Property`
            The EpochPosition error instance
        """
        err_instance = MivotInstance(dmtype=f"{ModelPrefix.mango}:EpochPositionErrors",
                                     dmrole=f"{ModelPrefix.mango}:EpochPosition.errors")

        for role, mapping in errors.items():
            error_class = mapping["class"]
            if (role in Roles.EpochPositionErrors
                    and error_class in ["PErrorSym2D", "PErrorSym1D", "PErrorAsym1D"]):
                err_instance.add_instance(
                    self._get_error_instance(error_class,
                                             f"{ModelPrefix.mango}:EpochPositionErrors.{role}",
                                             mapping))
        return err_instance

    def _add_epoch_position_epoch(self, **mapping):
        """
        Private method building and returning the observation date (DateTime) of the EpohPosition.

        Parameters
        ----------
        mapping: dict(representation, datetime)
                Mapping of the DateTime fields

        Returns
        -------
        `Property`
            The EpochPosition observation date instance
        """
        datetime_instance = MivotInstance(dmtype=f"{ModelPrefix.mango}:DateTime",
                                       dmrole=f"{ModelPrefix.mango}:EpochPosition.obsDate")

        representation = mapping.get("representation")
        value = mapping["dateTime"]
        if representation not in CoordSystems.time_formats:
            raise MappingError(f"epoch representation {representation} not supported. "
                               f"Take on of {CoordSystems.time_formats}")
        datetime_instance.add_attribute(IvoaType.string,
                                        f"{ModelPrefix.mango}:DateTime.representation",
                                        value=MivotUtils.as_literal(representation))
        datetime_instance.add_attribute(IvoaType.datetime,
                                        f"{ModelPrefix.mango}:DateTime.dateTime",
                                        value=value)
        return datetime_instance

    def add_epoch_position(self, space_frame_id, time_frame_id, mapping, semantics):
        """
        Add an ``EpochPosition`` instance to the properties of the current ``MangoObject``.
        Both mapping and semantics arguments inherit from
        `pyvo.mivot.writer.InstancesFromModels.add_mango_epoch_position`.

        Parameters
        ----------
        space_frame_id : string
            Identifier (dmid) of space system INSTANCE located in the GLOBALS
        time_frame_id : string
            Identifier (dmid) of time system INSTANCE located in the GLOBALS
        mapping : dict
            Mapping of the EpochPosition fields
        semantics : dict
            Mapping of the MangoObject property

        Returns
        -------
        `Property`
            The EpochPosition instance
        """
        ep_instance = Property(dmtype=f"{ModelPrefix.mango}:EpochPosition",
                                    semantics=semantics)
        MivotUtils.populate_instance(ep_instance, "EpochPosition",
                                     mapping, self._table, IvoaType.RealQuantity)
        if "obsDate" in mapping:
            ep_instance.add_instance(self._add_epoch_position_epoch(**mapping["obsDate"]))
        if "correlations" in mapping:
            ep_instance.add_instance(self._add_epoch_position_correlations(**mapping["correlations"]))
        if "errors" in mapping:
            ep_instance.add_instance(self._add_epoch_position_errors(**mapping["errors"]))
        if space_frame_id:
            ep_instance.add_reference(dmrole=f"{ModelPrefix.mango}:EpochPosition.spaceSys",
                                      dmref=space_frame_id)
        if time_frame_id:
            ep_instance.add_reference(dmrole=f"{ModelPrefix.mango}:EpochPosition.timeSys",
                                      dmref=time_frame_id)
        self._properties.append(ep_instance)
        return ep_instance

    def add_brightness_property(self, filter_id, mapping, semantics={}):
        """
        Add a ``Brightness`` instance to the properties of the current ``MangoObject``.
        Both mapping and semantics arguments inherit from
        `pyvo.mivot.writer.InstancesFromModels.add_mango_brightness`.

        Parameters
        ----------
        filter_id : string
            Identifier (dmid) of the PhotCal INSTANCE located in the GLOBALS
        mapping : dict
            Mapping of the EpochPosition fields
        semantics : dict
            Mapping of the MangoObject property

        Returns
        -------
        `Property`
            The Brightness instance
        """
        # create the MIVOT instance mapping the MANGO property
        mag_instance = Property(dmtype=f"{ModelPrefix.mango}:Brightness",
                                semantics=semantics)
        # set MANGO property attribute
        MivotUtils.populate_instance(mag_instance, "PhotometricProperty",
                                     mapping, self._table, IvoaType.RealQuantity)
        # build the error instance if it is mapped
        if "error" in mapping:
            error_mapping = mapping["error"]
            error_class = error_mapping["class"]
            mag_instance.add_instance(
                self._get_error_instance(error_class,
                                         f"{ModelPrefix.mango}:PhotometricProperty.error",
                                         error_mapping))
        # add MIVOT reference to the photometric calibration instance
        mag_instance.add_reference(dmrole=f"{ModelPrefix.mango}:Brightness.photCal", dmref=filter_id)
        self._properties.append(mag_instance)
        return mag_instance

    def add_color_instance(self, filter_low_id, filter_high_id, mapping, semantics={}):
        """
        Add an ``Color`` instance to the properties of the current ``MangoObject``.
        Both mapping and semantics arguments inherit from
        `pyvo.mivot.writer.InstancesFromModels.add_mango_color`.

        Parameters
        ----------
        filter_low_id : string
            Identifier (dmid) of the low energy Photfilter INSTANCE located in the GLOBALS
        filter_high_id : string
            Identifier (dmid) of the high energy Photfilter INSTANCE located in the GLOBALS
        mapping : dict
            Mapping of the EpochPosition fields
        semantics : dict
            Mapping of the MangoObject property

        Returns
        -------
        `Property`
            The Color instance
        """
        error_mapping = mapping["error"]
        mag_instance = Property(dmtype=f"{ModelPrefix.mango}:Color",
                                semantics=semantics)
        coldef_instance = MivotInstance(dmtype=f"{ModelPrefix.mango}:ColorDef",
                                        dmrole=f"{ModelPrefix.mango}:Color.colorDef")
        mapped_roles = MivotUtils._valid_mapped_dmroles(mapping.items(), "Color")
        def_found = False
        for dmrole, column in mapped_roles:
            if dmrole.endswith("definition"):
                def_found = True
                coldef_instance.add_attribute(dmtype="mango:ColorDefinition",
                                              dmrole="mango:ColorDef.definition",
                                              value=f"*{column}")
        if not def_found:
            raise MappingError("Missing color definition")
        mapping.pop("definition")
        MivotUtils.populate_instance(mag_instance, "PhotometricProperty", mapping,
                                     self._table, IvoaType.RealQuantity)
        coldef_instance.add_reference(dmrole=f"{ModelPrefix.mango}:ColorDef.low",
                                      dmref=filter_low_id)
        coldef_instance.add_reference(dmrole=f"{ModelPrefix.mango}:ColorDef.high",
                                      dmref=filter_high_id)
        error_class = error_mapping["class"]
        mag_instance.add_instance(self._get_error_instance(error_class,
                                                           f"{ModelPrefix.mango}:PhotometricProperty.error",
                                                           error_mapping))
        mag_instance.add_instance(coldef_instance)
        self._properties.append(mag_instance)
        return mag_instance

    def get_mango_object(self, with_origin=False):
        """
        Make and return the XML serialization of the MangoObject.

        Parameters
        ----------
        with_origin : bool
            Ask for adding a reference (_origin) to the query origin possibly located in the GLOBALS

        Returns
        -------
        string
            The XML serialization of the MangoObject
        """
        mango_object = MivotInstance(dmtype="mango:MangoObject", dmid=self._dmid)
        if self._dmid:
            ref, value = MivotUtils.get_ref_or_literal(self._dmid)
            att_value = ref if ref else value

            mango_object.add_attribute(dmrole="mango:MangoObject.identifier",
                                       dmtype=IvoaType.string,
                                       value=att_value)
        if with_origin:
            mango_object.add_reference("mango:MangoObject.queryOrigin", "_origin")
        m_properties = []
        for prop in self._properties:
            m_properties.append(prop.xml_string())
        mango_object.add_collection("mango:MangoObject.propertyDock", m_properties)
        return mango_object
