"""
Utility class to process XML.
"""
from pyvo.mivot.utils.xpath_utils import XPath
try:
    from defusedxml import ElementTree as etree
except ImportError:
    from xml.etree import ElementTree as etree
import xml.etree.ElementTree as ET
from pyvo.mivot.utils.vocabulary import Constant
from pyvo.mivot.utils.vocabulary import Att
from pyvo.mivot.utils.exceptions import ResolveException


class XmlUtils:
    """
    Static class implementing convenient operations on XML
    """
    @staticmethod
    def pretty_print(xmltree):
        """
        Pretty print an XML tree.
        Parameters
        ----------
        xmltree (~`xml.etree.ElementTree.Element`): XML tree to pretty print.
        """
        print(XmlUtils.pretty_string(xmltree))

    @staticmethod
    def pretty_string(xmltree):
        """
        Return a pretty string representation of an XML tree.
        Parameters
        ----------
        xmltree (~`xml.etree.ElementTree.Element`): XML tree to convert to a pretty string.
        Returns
        -------
        str: The pretty string representation of the XML tree.
        """
        if hasattr(xmltree, 'getroot'):
            XmlUtils.indent(xmltree.getroot())
            new_xml = ET.tostring(xmltree.getroot(), encoding='unicode')
        else:
            XmlUtils.indent(xmltree)
            new_xml = ET.tostring(xmltree, encoding='unicode')
        return new_xml.replace("ns0:", "")

    @staticmethod
    def indent(elem, level=0):
        """
        Indent an XML tree.
        Parameters
        ----------
        elem (~`xml.etree.ElementTree.Element`): XML tree to indent.
        level (int): level of indentation.
        Returns
        -------
        ~`xml.etree.ElementTree.Element`
            The indented XML tree.
        """
        i = "\n" + level * "  "
        j = "\n" + (level - 1) * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for subelem in elem:
                XmlUtils.indent(subelem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = j
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = j
        return elem

    @staticmethod
    def xmltree_from_file(file_path):
        """
        Parse an XML tree from a file.
        Parameters
        ----------
        file_path : str
            The path to the XML file.
        Returns
        -------
        ~`xml.etree.ElementTree.Element`
            The parsed XML tree.
        """
        return etree.parse(file_path)

    @staticmethod
    def xmltree_to_file(xmltree, file_path):
        """
        Write an XML tree to a file.
        Parameters
        ----------
        xmltree : ~`xml.etree.ElementTree.Element`
            The XML tree to write to the file.
        file_path : str
            The path to the output file.
        """
        with open(file_path, 'w') as output:
            output.write(XmlUtils.pretty_string(xmltree))

    @staticmethod
    def assertXmltreeEquals(xmltree1, xmltree2):
        """
        Assert that two XML trees are equal.
        Parameters
        ----------
        xmltree1 : ~`xml.etree.ElementTree.Element`
            The first XML tree for comparison.
        xmltree2 : ~`xml.etree.ElementTree.Element`
            The second XML tree for comparison.
        """
        xml_str1 = etree.tostring(xmltree1).decode("utf-8")
        xml_str2 = etree.tostring(xmltree2).decode("utf-8")
        checker = XMLOutputChecker()
        assert checker.check_output(xml_str1, xml_str2, 0), f"XML trees differ:\n{xml_str1}\n---\n{xml_str2}"

    @staticmethod
    def assertXmltreeEqualsFile(xmltree1, xmltree2_file):
        """
        Assert that an XML tree is equal to the content of a file.
        Parameters
        ----------
        xmltree1 : ~`xml.etree.ElementTree.Element`
            The XML tree for comparison.
        xmltree2_file : str
            The path to the file containing the second XML tree.
        """
        xmltree2 = XmlUtils.xmltree_from_file(xmltree2_file).getroot()
        xml_str1 = etree.tostring(xmltree1).decode("utf-8")
        xml_str2 = etree.tostring(xmltree2).decode("utf-8")
        checker = XMLOutputChecker()
        assert checker.check_output(xml_str1, xml_str2), f"XML trees differ:\n{xml_str1}\n---\n{xml_str2}"

    @staticmethod
    def set_column_indices(mapping_block, index_map):
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
                        raise ResolveException(
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
    def set_column_units(mapping_block, unit_map):
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


class XMLOutputChecker:
    """
    This class is used to compare XML outputs, ignoring whitespace differences.
    """
    def check_output(self, want, got):
        """
        Compare two XML outputs, ignoring whitespace differences.
        Parameters
        ----------
        want : str
            The expected XML output.
        got : str
            The actual XML output.
        Returns
        -------
        bool
            True if the two XML outputs are equal, False otherwise.
        """
        return self._format_xml(want.strip()) == self._format_xml(got.strip())

    def output_difference(self, want, got):
        """
        Return a string describing the differences between two XML outputs.
        Parameters
        ----------
        want : str
            The expected XML output.
        got : str
            The actual XML output.
        Returns
        -------
        str
            A string describing the differences between the two XML outputs.
        """
        return f"Diff:\n{self._format_xml(want)}\nvs.\n{self._format_xml(got)}"

    def _format_xml(self, xml_str):
        """
        Format an XML string.
        Parameters
        ----------
        xml_str : str
            The XML string to format.
        Returns
        -------
        str
            The formatted XML string.
        """
        return "\n".join(line.strip() for line in xml_str.splitlines())
