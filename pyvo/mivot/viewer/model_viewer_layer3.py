# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
ModelViewerLayer3 transform an XML instance into a nested dictionary representing all of its objects.
"""
from pyvo.mivot.utils.dict_utils import DictUtils
from pyvo.mivot.viewer.mivot_class import MivotClass
from pyvo.utils.prototype import prototype_feature


@prototype_feature('MIVOT')
class ModelViewerLayer3(object):
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
        Create recursively a nested dictionary from the XML tree structure keeping the hierarchy.
        Each object is represented in the dictionary by a new dictionary as dmrole: {}.
        Depending on the tag, elements will be processed differently:
         - INSTANCE will lead to a new dictionary.
         - COLLECTION will lead to a list.
         - ATTRIBUTE will lead to a leaf in the tree structure, with dmtype, dmrole, value, unit, ref.
        :param element: `~lxml.etree._Element` object
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
        ATTRIBUTE is always a leaf, so it is not recursive.
        :param child: child `~lxml.etree._Element`
        :rtype: {dmtype: @dmtype, dmrole: @dmrole, value: @value, unit: @unit, ref: @ref}
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
        COLLECTION is always represented as a list, we add each element of the COLLECTION in the list.
        :param child: child `~lxml.etree._Element`
        :rtype: [{},{}, ..]
        """
        retour = []
        for child_coll in child:
            retour.append(self._to_dict(child_coll))
        return retour

    def _cast_type_value(self, value, dmtype):
        """
        As the type of ATTRIBUTE values returned in the dictionary is string by default, we need to cast them.
        :param value: value of ATTRIBUTE
        :param dmtype: dmtype of ATTRIBUTE
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
