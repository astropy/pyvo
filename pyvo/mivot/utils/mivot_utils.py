'''
Utilities handling various operations on Mivot instances
'''
import numpy
from pyvo.mivot.utils.exceptions import MappingError
from pyvo.mivot.glossary import IvoaType, Roles, ModelPrefix


class MivotUtils:
    """
    Some utilities making easier the transformation of Mivot elements into dictionary components.
    These dictionaries are used to generate ``MivotInstance`` objects
    """

    @staticmethod
    def _valid_mapped_dmroles(mapped_roles, class_name):
        """
        Check that the given mapped roles of the given class, are in the `pyvo.mivot.glossary.Roles`,
        which reflects the model.

        Parameters
        ----------
        mapped_roles: dict
            Dictionary of the matches between the dmroles (dict keys) and
            the column identifiers (dict values). This mapping is a user input.
        class_name: str
            Name of the class to which the mapping applies

        Returns
        -------
        dict
            The dictionary of valid matches between the dmroles (dict keys) and
            the column identifiers (dict values).

        Raises
        ------
        MappingError
            If the class ``class_name`` is not supported or if
            some mapped role does not exist for the glossary
        """
        # Check that the class is in the glossary
        if not hasattr(Roles, class_name):
            raise MappingError(f"Unknown or unimplemented class {class_name}")
        # get the list of supported roles
        dmroles = getattr(Roles, class_name)
        real_mapping = []
        for mapped_role, column in mapped_roles:
            # 'class' is a reserved word, not a role
            if mapped_role == "class" or isinstance(column, dict) or isinstance(column, list):
                continue

            found = False
            for leaf in dmroles:
                dmrole = f"{ModelPrefix.mango}:{class_name}.{leaf}"
                if dmrole.lower().endswith("." + mapped_role.lower()):
                    real_mapping.append((dmrole, column))
                    found = True
                    break
            if not found:
                raise MappingError(f"Class {ModelPrefix.mango}:{class_name} "
                                   f"has no {mapped_role} attribute."
                                   f"Supported roles are {dmroles}")

        return real_mapping

    @staticmethod
    def xml_to_dict(element):
        """
        Recursively create a nested dictionary from the XML tree structure,
        preserving the hierarchy.
        The processing of elements depends on the tag:

         - For INSTANCE, a new dictionary is created.
         - For COLLECTION, a list is created.
         - For ATTRIBUTE, a leaf structure is created in the tree structure with dmtype,
           dmrole, value, unit, and ref keys.

        Parameters
        ----------
        element : `xml.etree.ElementTree.Element`
            The XML element to convert to a dictionary

        Returns
        -------
        dict
            The nested dictionary representing the XML tree structure.
        """
        dict_result = {}
        for key, value in element.attrib.items():
            dict_result[key] = value
        for child in element:
            dmrole = child.get("dmrole")
            if child.tag == "ATTRIBUTE":
                dict_result[dmrole] = MivotUtils._attribute_to_dict(child)
            elif child.tag == "INSTANCE":  # INSTANCE is recursively well managed by the function _to_dict
                dict_result[dmrole] = MivotUtils.xml_to_dict(child)
            elif child.tag == "COLLECTION":
                dict_result[dmrole] = MivotUtils._collection_to_dict(child)
        return dict_result

    @staticmethod
    def _attribute_to_dict(child):
        """
        Convert an ATTRIBUTE (XML) element to a dictionary.
        ATTRIBUTE being always a leaf, the conversion is not recursive.

        Parameters
        ----------
        child : `xml.etree.ElementTree.Element`
             ATTRIBUTE XML element to convert.

        Returns
        -------
        dict:
            A dictionary representing the ATTRIBUTE element with keys:
            'dmtype', 'dmrole', 'value', 'unit', and 'ref'.
        """
        attribute = {}
        if child.get("dmtype") is not None:
            attribute["dmtype"] = child.get("dmtype")
        if child.get("value") is not None:
            attribute["value"] = MivotUtils.cast_type_value(child.get("value"), child.get("dmtype"))
        else:
            attribute["value"] = None
        if child.get("unit") is not None:
            attribute["unit"] = child.get("unit")
        else:
            attribute["unit"] = None
        if child.get("ref") is not None:
            attribute["ref"] = child.get("ref")
        else:
            attribute["ref"] = None
        return attribute

    @staticmethod
    def _collection_to_dict(child):
        """
        Convert a COLLECTION element (child) to a list of dictionaries.

        Parameters
        ----------
        child : `xml.etree.ElementTree.Element`
            COLLECTION XML element to convert

        Returns
        -------
        list({})
            list of dictionaries representing the COLLECTION items
        """
        collection_items = []
        for child_coll in child:
            collection_items.append(MivotUtils.xml_to_dict(child_coll))
        return collection_items

    @staticmethod
    def cast_type_value(value, dmtype):
        """
        Cast value to the Python type matching dmtype.

        Parameters
        ----------
        value : str
            value to cast
        dmtype : str
            model dmtype

        Returns
        -------
        Union[bool, float, str, None]
            The casted value or None
        """
        lower_dmtype = dmtype.lower()
        # empty strings cannot be casted
        if "string" not in lower_dmtype and value == "":
            return None
        if numpy.issubdtype(type(value), numpy.floating):
            return float(value)
        if isinstance(value, str):
            lower_value = value.lower()
        else:
            lower_value = value
        if "bool" in lower_dmtype:
            if value == "1" or lower_value == "true" or lower_value:
                return True
            else:
                return False
        elif lower_value in ('notset', 'noset', 'null', 'none', 'nan') or value is None:
            return None
        elif (isinstance(value, numpy.ndarray) or isinstance(value, numpy.ma.core.MaskedConstant)
              or value == '--'):
            return None
        elif "real" in lower_dmtype or "double" in lower_dmtype or "float" in lower_dmtype:
            return float(value)
        else:
            return value

    @staticmethod
    def format_dmid(dmid):
        """
        Replace characters that could confuse XPath queries with '_'.
        This is not required by the MIVOT schema but this makes this API more robust

        Returns
        -------
        str
            formatted dmid
        """
        if dmid is not None:
            return dmid.replace("/", "_").replace(".", "_").replace("-", "_")
        return ""

    @staticmethod
    def get_field_attributes(table, column_id):
        """
        Parameters
        ----------
        table : astropy.table
            Table (from parsed VOTable) of the mapped data
        column_id : str
            Identifier of the table column from which we want to get the unit

        Returns
        -------
        unit, ref, literal
        """
        ref, literal = MivotUtils.get_ref_or_literal(column_id)
        if literal:
            return None, None, literal
        else:
            try:
                field = table.get_field_by_id_or_name(ref)
                return str(field.unit), column_id, None
            except KeyError as keyerror:
                raise MappingError(f"Cannot find any field identified by {column_id}") from keyerror

    @staticmethod
    def get_ref_or_literal(value_or_ref):
        """
        Check if value_or_ref must be interpreted as a column reference or a literal.

        Returns
        -------
           (ref, literal)
        """
        if not value_or_ref:
            raise MappingError("An attribute cannot be set with a None value")
        elif isinstance(value_or_ref, str):
            return ((None, value_or_ref.replace("*", "")) if value_or_ref.startswith("*")
                    else (value_or_ref, None))
        else:
            return (None, value_or_ref)

    @staticmethod
    def as_literal(identifier):
        """
        Make sure the identifier will be interpreted as a literal (* prefix).
        Literal are either non string values or strings starting with a *

        Parameters
        ----------
        identifier: str
            column identifier or literal value

        Returns
        -------
        str
            identifier prefixes with a *
        """
        if isinstance(identifier, str) and not identifier.startswith("*"):
            return "*" + identifier
        return identifier

    @staticmethod
    def populate_instance(property_instance, class_name,
                          mapping, table, dmtype, as_literals=False, package=None):
        """
        This function inserts in the property_instance all expected attributes.

        - The structure of the class is supposed to be flat (only ATTRIBUTEs).
        - All attributes are meant to have the same dmtype.
        - The mapping is checked against the `pyvo.mivot.glossary.Roles`.

        Parameters
        ----------
        property_instance : `pyvo.mivot.writer.instance.MivotInstance`
            Mivot instance to populate with attributes
        class_name : str
            Name of the property_instance class (dmtype).
            Used to get all the attribute roles (given by the model) of the class
        mapping : dict
            Dictionary associating model roles with their values.
        table : astropy.table
            Table (from parsed VOTable) of the mapped data
        dmtype : string
            common dmtype of object attributes
        as_literal : boolean, optional (default isTrue)
            If True, all attribute are set with literal values (@value="...")
        package : str, optional (default as None)
            Package name possibly prefixing dmroles
        """
        mapped_roles = MivotUtils._valid_mapped_dmroles(mapping.items(), class_name)
        pkg = f"{package}." if package else ""
        for dmrole, column in mapped_roles:
            # minimal reserved characters escaping
            if isinstance(column, str):
                column = column.replace("&", "&amp;")
            # force column references to be processed as literals if requested
            if as_literals:
                column = MivotUtils.as_literal(column)
            unit, _, _ = MivotUtils.get_field_attributes(table, column)
            if isinstance(column, bool):
                r_dmtype = IvoaType.bool
            else:
                r_dmtype = dmtype
            r_dmrole = dmrole.replace(":", f":{pkg}")
            property_instance.add_attribute(dmtype=r_dmtype,
                                       dmrole=r_dmrole,
                                       value=column,
                                       unit=unit)
