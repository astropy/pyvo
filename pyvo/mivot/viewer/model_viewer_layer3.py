# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
ModelViewerLayer3 transform an XML instance into a nested dictionary representing all of its objects.
"""
from pyvo.mivot.utils.dict_utils import DictUtils
from pyvo.mivot.viewer.mivot_class import MivotClass
from pyvo.utils.prototype import prototype_feature


@prototype_feature('MIVOT')
class ModelViewerLayer3:
    """
    The ModelViewerLayer3 take as an argument a xml INSTANCE and give from this xml a nested
    dictionary that represents all objects of the xml INSTANCE with their hierarchy.
    From this dictionary, we build a `~pyvo.mivot.viewer.mivot_class.MivotClass` object
    which is a dictionary with only essential information used to process data.
    """

    def __init__(self, xml_instance):
        self._xml_instance = xml_instance
        self._dict = self._to_dict(self._xml_instance)
        self.mivot_class = MivotClass(**self._dict)

    def get_row_instance(self):
        """
        Returns the dictionary of the `~pyvo.mivot.viewer.mivot_class.MivotClass`,
        i.e., the dictionary of all objects of the xml instance. It can be easily navigated.
        """
        return self.mivot_class.__dict__

    def show_class_dict(self):
        """
        Returns the dictionary of the INSTANCE objects in a JSON format.
        """
        return DictUtils.print_pretty_json(self.mivot_class.display_class_dict(self.get_row_instance()))

    def _to_dict(self, element):
        """
        Recursively creates a nested dictionary from the XML tree structure, preserving the hierarchy.

        Each object in the dictionary is represented by a new dictionary with dmrole: {}.
        The processing of elements depends on the tag:
         - For INSTANCE, a new dictionary is created.
         - For COLLECTION, a list is created.
         - For ATTRIBUTE, a leaf is created in the tree structure with dmtype, dmrole, value, unit, and ref.

        Parameters
        ----------
        element : ~`xml.etree.ElementTree.Element`
            The XML element to convert to a dictionary.

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
                dict_result[dmrole] = self._attribute_to_dict(child)
            elif child.tag == "INSTANCE":  # INSTANCE is recursively well managed by the function _to_dict
                dict_result[dmrole] = self._to_dict(child)
            elif child.tag == "COLLECTION":
                dict_result[dmrole] = self._collection_to_dict(child)
        return dict_result

    def _attribute_to_dict(self, child):
        """
        Converts an ATTRIBUTE element to a dictionary.
        ATTRIBUTE is always a leaf, so it is not recursive.

        Parameters
        ----------
        child : ~`xml.etree.ElementTree.Element`
            The ATTRIBUTE XML element to convert.

        Returns
        -------
        dict
            A dictionary representing the ATTRIBUTE element with keys:
            'dmtype', 'dmrole', 'value', 'unit', and 'ref'.
        """
        attribute = {}
        if child.get('dmtype') is not None:
            attribute['dmtype'] = child.get("dmtype")
        if child.get("value") is not None:
            attribute['value'] = self._cast_type_value(child.get("value"), child.get("dmtype"))
        else:
            attribute['value'] = None
        if child.get("unit") is not None:
            attribute['unit'] = child.get("unit")
        else:
            attribute['unit'] = None
        if child.get("ref") is not None:
            attribute['ref'] = child.get("ref")
        else:
            attribute['ref'] = None
        return attribute

    def _collection_to_dict(self, child):
        """
        Converts a COLLECTION element to a list of dictionaries.
        COLLECTION is always represented as a list, and each element of the COLLECTION is added to the list.

        Parameters
        ----------
        child : `~`xml.etree.ElementTree.Element``
            The COLLECTION XML element to convert.

        Returns
        -------
        list
            A list of dictionaries representing the elements of the COLLECTION.
        """
        retour = []
        for child_coll in child:
            retour.append(self._to_dict(child_coll))
        return retour

    def _cast_type_value(self, value, dmtype):
        """
        Casts the value of an ATTRIBUTE based on its dmtype.
        As the type of ATTRIBUTE values returned in the dictionary is string by default,
        this function is used to cast them based on their dmtype.

        Parameters
        ----------
        value : str
            The value of the ATTRIBUTE.
        dmtype : str
            The dmtype of the ATTRIBUTE.

        Returns
        -------
        Union[bool, float, str, None]
            The casted value based on the dmtype.
        """
        lower_dmtype = dmtype.lower()
        lower_value = value.lower()
        if "bool" in lower_dmtype:
            if value == "1" or "true" in lower_value:
                return True
            else:
                return False
        elif lower_value in ('notset', 'noset', 'null', 'none'):
            return None
        elif "real" in lower_dmtype or "double" in lower_dmtype or "float" in lower_dmtype:
            return float(value)
        else:
            return value
