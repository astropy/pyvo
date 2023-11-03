"""
Created on 11 Dec 2021

@author: laurentmichel
"""
from pyvo.mivot.utils.exceptions import MivotElementNotFound, MappingException
from pyvo.mivot.utils.vocabulary import Att, Ele
from pyvo.mivot import logger
from pyvo.mivot.utils.constant import Constant
from pyvo.utils.prototype import prototype_feature


@prototype_feature('MIVOT')
class AnnotationSeeker(object):
    """
    This class provides tools extracting mapping sub-blocks that are often used by other stakeholders.
    All functions using the mapping are using this class to get XML elements.
    To make the job simpler for other tools, the XML namespace is removed from the mapping block whatever it is.
    This is usually done by Astropy as well.
    """

    def __init__(self, xml_block):
        """
        - Split the mapping as elements of interest
        - remove the name_spaces
        - Append numbers to JOIN/REFERENCE
        :param xml_block: XML mapping block (etree.Element)
        """
        # Full mapping blocks
        self._xml_block = xml_block
        # GLOBALS bock
        self._globals_block = None
        # Templates dictionary {tableref: XML-TEMPLATES}
        self._templates_blocks = {}

        # Find the GLOBALS block
        self._find_globals_block()
        # Find the TEMPLATES blocks
        self._find_templates_blocks()
        # Remove the namespaces from specific elements and make them unique
        self._rename_ref_and_join()

    def _find_globals_block(self):
        """
        Finds and sets the GLOBALS block within the XML mapping block.
        """
        for child in self._xml_block:
            if self._name_match(child.tag, Ele.GLOBALS):
                logger.info("Found "+Ele.GLOBALS)
                self._globals_block = child

    def _find_templates_blocks(self):
        """
        Finds and sets the TEMPLATES blocks within the XML mapping block.
        """
        for child in self._xml_block:
            if self._name_match(child.tag, Ele.TEMPLATES):
                tableref = child.get(Att.tableref)
                if tableref is not None:
                    logger.info("Found "+Ele.TEMPLATES+" %s", tableref)
                    self._templates_blocks[tableref] = child
                elif not self._templates_blocks:
                    logger.info("Found "+Ele.TEMPLATES+" without "+Att.tableref)
                    self._templates_blocks["DEFAULT"] = child
                else:
                    raise MivotElementNotFound(Ele.TEMPLATES+" without "+Att.tableref+" must be unique")

    def _rename_ref_and_join(self):
        """
        Removes namespaces from specified elements and makes them unique.
        """
        cpt = 1
        for tag in ['REFERENCE', 'JOIN']:
            xpath = '//' + tag
            for ele in self._xml_block.xpath(xpath):
                ele.tag = tag + '_' + str(cpt)
                cpt += 1

    def _name_match(self, name, expected):
        """
        Returns true if name matches expected whatever the namespace
        :param name: Name to compare
        :param expected: Expected name for the comparison
        """
        if type(name).__name__ == 'cython_function_or_method':
            return False
        return name.endswith(expected)

    """
    Properties
    """

    @property
    def globals_block(self):
        """
        GLOBALS getter
        """
        return self._globals_block

    @property
    def globals_collections(self):
        """
        Returns the list of all GLOBALS/COLLECTION elements.
        These collections have no dmroles but often dmids.
        They have particular roles
        - Used by references (e.g., filter definition)
        - Used as head of the mapped model (e.g., [Cube instance])
        """
        return self._globals_block.xpath("//GLOBALS/COLLECTION")

    @property
    def models(self):
        """
        Gets the MODELs and their URLs, return it as a dictionary
        :rtype: {'model': [url], ...}
        """
        retour = {}
        eset = self._xml_block.xpath("//"+Ele.MODEL)
        for ele in eset:
            retour[ele.get("name")] = ele.get("url")
        return retour

    @property
    def templates_tableref(self):
        """
        Return the list of all the @tableref found in the mapping
        """
        return self._templates_blocks.keys()

    @property
    def templates(self):
        """
        Return a list of TEMPLATES tablerefs
        :rtype: ['tableref', ...]
        """
        retour = []
        eset = self._xml_block.xpath(".//"+Ele.TEMPLATES)
        for ele in eset:
            tableref = ele.get("tableref")
            if tableref is None:
                tableref = Constant.FIRST_TABLE
            retour.append(tableref)
        return retour

    def get_templates_block(self, tableref):
        """
        Return the TEMPLATES mapping block of the table matching @tableref
        if no tableref is None returns all values of templates_blocks.
        :param tableref:
        :rtype:
        """
        # one table: name forced to DEFAULT or take the first
        if tableref is None:
            for _, tmpl in self._templates_blocks.items():
                return tmpl
        return self._templates_blocks[tableref]

    """
    INSTANCE
    """
    def get_instance_dmtypes(self):
        """
        Gets @dmtypes of all mapped instances
        :rtype: {GLOBALS: [], TEMPLATES: {}}
        """
        retour = {Ele.GLOBALS: [], Ele.TEMPLATES: {}}

        eset = self._globals_block.xpath(".//"+Ele.INSTANCE)
        for ele in eset:
            retour[Ele.GLOBALS].append(ele.get(Att.dmtype))

        for tableref, block in self._templates_blocks.items():
            retour[Ele.TEMPLATES][tableref] = []
            eset = block.xpath(".//"+Ele.INSTANCE)
            for ele in eset:
                retour[Ele.TEMPLATES][tableref].append(ele.get(Att.dmtype))
        return retour

    def get_instance_by_dmtype(self, dmtype_pattern):
        """
        Gets all the mapped instances that have a @dmtype containing dmtype_pattern
        :param dmtype_pattern: @dmtype looked for
        :rtype: {GLOBALS: [], TEMPLATES: {}}
        """
        retour = {Ele.GLOBALS: [], Ele.TEMPLATES: {}}

        eset = self._globals_block.xpath(".//"+Ele.INSTANCE+"[contains(@"+Att.dmtype+",'"+dmtype_pattern+"')]")
        retour[Ele.GLOBALS] = eset

        for tableref, block in self._templates_blocks.items():
            retour[Ele.TEMPLATES][tableref] = block.xpath(".//"+Ele.INSTANCE+"[contains(@"+Att.dmtype+",'"+
                                                          dmtype_pattern+"')]")
        return retour

    """
    GLOBALS INSTANCES
    """
    def get_globals_instances(self):
        """
        Returns the list of all GLOBALS/INSTANCE elements.
        These collections have no dmroles but often dmids.
        They have particular roles
        - Used by references (e.g., filter definition)
        - Used as head of the mapped model (e.g., Cube instance)
        """
        return self._globals_block.xpath("//"+Ele.GLOBALS+"/"+Ele.INSTANCE)

    def get_globals_instance_dmids(self):
        """
        Gets a list of @dmid for GLOBALS/INSTANCE
        """
        retour = []
        eset = self._globals_block.xpath("//"+Ele.INSTANCE+"[@"+Att.dmid+"]")
        for ele in eset:
            retour.append(ele.get(Att.dmid))
        return retour

    def get_globals_instance_by_dmid(self, dmid):
        """
        Gets the GLOBALS/INSTANCE with @dmid=dmid
        :param dmid: searched @dmid
        """
        eset = self._globals_block.xpath("//"+Ele.INSTANCE+"[@"+Att.dmid+"='" + dmid + "']")
        for ele in eset:
            return ele
        return None

    def get_globals_instance_dmtypes(self):
        """
        Gets the list the @dmtype GLOBALS/INSTANCE
        """
        retour = []
        for inst in self.get_globals_instances():
            retour.append(inst.get(Att.dmtype))
        return retour

    def get_templates_instance_by_dmid(self, tableref, dmid):
        """
        Gets the TEMPLATES/INSTANCE with @dmid=dmid and TEMPLATES@tableref=tableref
        :param tableref: @tableref of the searched TEMPLATES
        :param dmid: searched @dmid
        """
        templates_block = self.get_templates_block(tableref)
        if templates_block is None:
            return None
        eset = templates_block.xpath(".//"+Ele.INSTANCE+"[@"+Att.dmid+"='" + dmid + "']")
        for ele in eset:
            return ele
        return None

    def get_globals_instance_from_collection(self, sourceref, pk_value):
        """
        Gets the GLOBALS/COLLECTION[@dmid=sourceref]/INSTANCE/PRIMARY_KEY[@value='pk_value']
        :param sourceref: searched @dmid of COLLECTION
        :param pk_value: searched @value of PRIMARY_KEY
        :rtype: `~lxml.etree._Element`
        """
        einst = self._globals_block.xpath("//"+Ele.COLLECTION+"[@"+Att.dmid+"='" + sourceref
                                          + "']/"+Ele.INSTANCE+"/"+Att.primarykey+"[@"+Att.value+"='" + pk_value + "']")
        for inst in einst:
            return inst.getparent()
        return None

    """
    GLOBALS COLLECTION
    """

    def get_globals_collection(self, dmid):
        """
        Gets the GLOBALS/COLLECTION with @dmid=dmid
        :param dmid: searched @dmid
        """
        eset = self._globals_block.xpath("//"+Ele.GLOBALS+"/"+Ele.COLLECTION+"[@"+Att.dmid+"='" + dmid + "']")
        for ele in eset:
            return ele
        return None

    def get_globals_collection_dmids(self):
        """
        Gets the list of all the @dmid of GLOBALS/COLLECTION
        """
        retour = []
        eset = self._globals_block.xpath("//"+Ele.COLLECTION+"[@"+Att.dmid+"]")
        for ele in eset:
            retour.append(ele.get(Att.dmid))
        return retour

    def get_globals_collection_dmtypes(self):
        """
        Gets the list of the @dmtype of GLOBALS/COLLECTION/INSTANCE
        Used for collections of static objects
        """
        eles = self._globals_block.xpath("//"+Ele.GLOBALS+"/"+Ele.COLLECTION+"/"+Ele.INSTANCE+"")
        retour = []
        for inst in eles:
            dmtype = inst.get(Att.dmtype)
            if dmtype not in retour:
                retour.append(dmtype)
        return retour

    def get_collection_item_by_primarykey(self, coll_dmid, key_value):
        """
        Get the GLOBALS/COLLECTION/INSTANCE with COLLECTION@dmid=dmid and
        INSTANCE with a PRIMARY_key which @value matches key_value
        An exception is risen if there is less or more than one element matching the criteria.
        The 2 parameters match the dynamic REFERENCE definition
        :param coll_dmid: searched @dmid of COLLECTION
        :param key_value: searched @value of PRIMARY_KEY
        :rtype: []
        """
        eset = self._globals_block.xpath(".//"+Ele.COLLECTION+"[@"+Att.dmid+"='" + coll_dmid+ "']/"
                                         +Ele.INSTANCE+"/"+Att.primarykey+"[@"+Att.value+"='" + key_value + "']")
        if len(eset) == 0:
            raise MivotElementNotFound(Ele.INSTANCE+" with "+Att.primarykey+f" = {key_value} in "
                                   +Ele.COLLECTION+" "+Att.dmid+f" {key_value} not found")
        if len(eset) > 1:
            raise MappingException("More than one "+Ele.INSTANCE+" with "+Att.primarykey+
                                   f" = {key_value} found in "+Ele.COLLECTION+" "+Att.dmid+f" {key_value}")
        logger.debug(Ele.INSTANCE+" with "+Att.primarykey+"=%s found in "+Ele.COLLECTION+" "+Att.dmid+"=%s",
                     key_value, coll_dmid)
        return eset[0].getparent()
