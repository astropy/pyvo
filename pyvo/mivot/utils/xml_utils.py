"""
Utility class to process XML.
"""
from lxml import etree
from pyvo.mivot.utils.constant import Constant
from pyvo.mivot.utils.vocabulary import Att
from doctest import Example
from lxml.doctestcompare import LXMLOutputChecker


class XmlUtils(object):
    """
    Static class implementing convenient operations on XML.
    """

    @staticmethod
    def pretty_print(xmltree):
        """
        Pretty print an XML tree.

        Parameters
        ----------
        xmltree : lxml.etree._ElementTree
            The XML tree to pretty print.
        """
        print(XmlUtils.pretty_string(xmltree))

    @staticmethod
    def pretty_string(xmltree):
        """
        Return a pretty string representation of an XML tree.

        Parameters
        ----------
        xmltree : lxml.etree._ElementTree
            The XML tree to convert to a pretty string.

        Returns
        -------
        str
            The pretty string representation of the XML tree.
        """
        etree.indent(xmltree, space="   ")
        return etree.tostring(xmltree, pretty_print=True).decode("utf-8")

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
        lxml.etree._ElementTree
            The parsed XML tree.
        """
        return etree.parse(file_path)

    @staticmethod
    def xmltree_to_file(xmltree, file_path):
        """
        Write an XML tree to a file.

        Parameters
        ----------
        xmltree : lxml.etree._ElementTree
            The XML tree to write to the file.
        file_path : str
            The path to the output file.
        """
        with open(file_path, 'w') as output:
            output.write(XmlUtils.pretty_string(xmltree))

    @staticmethod
    def assertXmltreeEquals(xmltree1, xmltree2, message):
        """
        Assert that two XML trees are equal.

        Parameters
        ----------
        xmltree1 : lxml.etree._ElementTree
            The first XML tree for comparison.
        xmltree2 : lxml.etree._ElementTree
            The second XML tree for comparison.
        message : str
            The message to display if the trees are not equal.
        """
        xml_str1 = etree.tostring(xmltree1, pretty_print=True).decode("utf-8")
        xml_str2 = etree.tostring(xmltree2, pretty_print=True).decode("utf-8")
        checker = LXMLOutputChecker()
        if not checker.check_output(xml_str1, xml_str2, 0):
            message = checker.output_difference(Example("", xml_str1), xml_str1, 0)
            raise AssertionError(message)

    @staticmethod
    def assertXmltreeEqualsFile(xmltree1, xmltree2_file, message=""):
        """
        Assert that an XML tree is equal to the content of a file.

        Parameters
        ----------
        xmltree1 : lxml.etree._ElementTree
            The XML tree for comparison.
        xmltree2_file : str
            The path to the file containing the second XML tree.
        message : str
            The message to display if the trees are not equal.
        """
        xmltree2 = XmlUtils.xmltree_from_file(xmltree2_file)
        xml_str1 = etree.tostring(xmltree1, pretty_print=True).decode("utf-8")
        xml_str2 = etree.tostring(xmltree2, pretty_print=True).decode("utf-8")
        checker = LXMLOutputChecker()
        if not checker.check_output(xml_str1, xml_str2, 0):
            message = checker.output_difference(Example("", xml_str2), xml_str1, 0)
            raise AssertionError(message)

    @staticmethod
    def set_column_indices(mapping_block, index_map):
        """
        Add column ranks to attributes having a ref.
        Using ranks allows identifying columns even when NumPy arrays have been serialized as [].

        Parameters
        ----------
        mapping_block : lxml.etree._ElementTree
            The XML mapping block.
        index_map : dict
            A dictionary mapping ref values to column indices.
        """
        for ele in mapping_block.xpath("//ATTRIBUTE"):
            ref = ele.get(Att.ref)
            if ref is not None and ref != Constant.NOT_SET:
                ele.attrib[Constant.COL_INDEX] = str(index_map[ref])

    @staticmethod
    def set_column_units(mapping_block, unit_map):
        """
        Add field units to attributes having a ref.
        Used for performing unit conversions.

        Parameters
        ----------
        mapping_block : lxml.etree._ElementTree
            The XML mapping block.
        unit_map : dict
            A dictionary mapping ref values to units.
        """
        for ele in mapping_block.xpath("//ATTRIBUTE"):
            ref = ele.get(Att.ref)
            if ref is not None and ref != Constant.NOT_SET:
                unit = unit_map[ref]
                if unit is None:
                    unit = ""
                else:
                    unit = unit.__str__()
                ele.attrib[Constant.FIELD_UNIT] = unit
