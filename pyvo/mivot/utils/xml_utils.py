"""
Created on 16 Dec 2021

@author: laurentmichel
"""
from lxml import etree
from pyvo.mivot.utils.constant import Constant

from doctest import Example
from lxml.doctestcompare import LXMLOutputChecker


class XmlUtils(object):
    """
    classdocs
    """

    @staticmethod
    def pretty_print(xmltree):
        print(XmlUtils.pretty_string(xmltree))

    @staticmethod
    def pretty_string(xmltree):
        etree.indent(xmltree, space="   ")
        return etree.tostring(xmltree, pretty_print=True).decode("utf-8")

    @staticmethod
    def xmltree_from_file(file_path):
        return etree.parse(file_path)

    @staticmethod
    def xmltree_to_file(xmltree, file_path):
        with open(file_path, 'w') as output:
            output.write(XmlUtils.pretty_string(xmltree))

    @staticmethod
    def assertXmltreeEquals(xmltree1, xmltree2, message):
        xml_str1 = etree.tostring(xmltree1, pretty_print=True).decode("utf-8")
        xml_str2 = etree.tostring(xmltree2, pretty_print=True).decode("utf-8")
        checker = LXMLOutputChecker()
        if not checker.check_output(xml_str1, xml_str2, 0):
            message = checker.output_difference(Example("", xml_str1), xml_str1, 0)
            raise AssertionError(message)

    @staticmethod
    def assertXmltreeEqualsFile(xmltree1, xmltree2_file, message=""):
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
        Add column ranks to attribute having a ref.
        Using ranks allow to identify columns even numpy raw have been serialised as [].
        """
        for ele in mapping_block.xpath("//ATTRIBUTE"):
            ref = ele.get("ref")
            if ref is not None and ref != 'NotSet':
                ele.attrib[Constant.COL_INDEX] = str(index_map[ref])

    @staticmethod
    def set_column_units(mapping_block, unit_map):
        """
        Add field unit to attribute having a ref.
        Used for performing unit conversions.
        """
        for ele in mapping_block.xpath("//ATTRIBUTE"):
            ref = ele.get("ref")
            if ref is not None and ref != 'NotSet':
                unit = unit_map[ref]
                if unit is None:
                    unit = ""
                else:
                    unit = unit.__str__()
                ele.attrib[Constant.FIELD_UNIT] = unit
