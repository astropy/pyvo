"""
Utility class to process XML.
"""
import re
from pyvo.mivot.utils.xpath_utils import XPath
import xml.etree.ElementTree as ET
from xml.dom import minidom
from pyvo.mivot.utils.vocabulary import Constant
from pyvo.mivot.utils.vocabulary import Att
from pyvo.mivot.utils.exceptions import MivotError


class XmlUtils:
    """
    Static class implementing convenient operations on XML
    """
    @staticmethod
    def pretty_print(xmltree, *, lshift=""):
        """
        Pretty print an XML tree

        Parameters
        ----------
        xmltree: (~`xml.etree.ElementTree.Element`)
            XML tree to pretty print

        lshift : str, optional, default ""
            Sequence to be inserted at the beginning of each line
            Usually a space sequence
        """
        print(XmlUtils.pretty_string(xmltree, lshift=lshift))

    @staticmethod
    def pretty_string(xmltree, *, lshift="", clean_namespace=True):
        """
        Return a pretty string representation of an XML tree (as Etree or string)

        Parameters
        ----------
        xmltree (~`xml.etree.ElementTree.Element`) or string:
            XML tree to convert to a pretty string

        lshift : str, optional, default ""
            Sequence to be inserted at the beginning of each line
            Usually a space sequence

        clean_namespace : boolean, optional, default True
            Default namespace (ns0) removed from element names if True

        Returns
        -------
        str: The pretty string representation of the XML tree.
        """
        if isinstance(xmltree, str):
            root = xmltree
        else:
            if hasattr(xmltree, 'getroot'):
                root = ET.tostring(xmltree.getroot(), encoding='unicode')
            else:
                root = ET.tostring(xmltree, encoding='unicode')
            root = root.replace("<?xml version=\"1.0\" ?>\n", "")
        reparsed = minidom.parseString(root)
        pretty_string = re.sub(r" +\n", "", reparsed.toprettyxml(indent="  "))
        pretty_string = pretty_string.replace("<?xml version=\"1.0\" ?>\n", "") \
                                     .replace("\n\n", "\n") \
                                     .replace("<", f"{lshift}<")

        if clean_namespace:
            return pretty_string.replace("ns0:", "")
        else:
            return pretty_string

    @staticmethod
    def strip_xml(xml_string):
        """
        Strip unnecessary whitespace and newline characters from an XML string.
        Used by unit tests to compare xml strings

        Parameters:
        - xml_string (str): The XML string to strip.

        Returns:
        - str: The stripped XML string.
        """
        return (
            xml_string.replace("\n", "").replace(" ", "").replace("'", "").replace('"', "")
        )

    @staticmethod
    def add_column_indices(mapping_block, index_map):
        """
        Add column ranks to attributes having a ref.
        Using ranks allows identifying columns even when NumPy arrays have been serialized as [].
        Parameters
        ----------
        mapping_block : ~`xml.etree.ElementTree.Element`
            The XML mapping block.
        index_map : dict
            A dictionary mapping ref values to column indices.
        """
        for ele in XPath.x_path(mapping_block, ".//ATTRIBUTE"):
            attr_ref = ele.get(Att.ref)
            if attr_ref is not None and attr_ref != Constant.NOT_SET:
                field_desc = None
                if attr_ref in index_map:
                    field_desc = index_map[attr_ref]
                else:
                    for _, value in index_map.items():
                        if value["ID"] == attr_ref:
                            field_desc = value
                            break
                if not field_desc:
                    if not ele.get(Att.value):
                        raise MivotError(
                            f"Attribute {ele.get(Att.dmrole)} can not be set:"
                            f" references a non existing column: {attr_ref} "
                            f"and has no default value")
                    else:
                        ele.attrib.pop(Att.ref, None)
                if field_desc:
                    ele.attrib[Constant.COL_INDEX] = str(field_desc["indx"])
                    if field_desc["ID"] != attr_ref:
                        ele.set(Att.ref, field_desc["ID"])

    @staticmethod
    def add_column_units(mapping_block, unit_map):
        """
        Add field units to attributes having a ref.
        Used for performing unit conversions.
        Parameters
        ----------
        mapping_block : ~`xml.etree.ElementTree.Element`
            The XML mapping block.
        unit_map : dict
            A dictionary mapping ref values to units.
        """
        for ele in XPath.x_path(mapping_block, ".//ATTRIBUTE"):
            ref = ele.get(Att.ref)
            if ref is not None and ref != Constant.NOT_SET:
                unit = None
                if ref in unit_map:
                    unit = unit_map[ref].__str__()
                else:
                    unit = ""
                ele.attrib[Constant.FIELD_UNIT] = unit
