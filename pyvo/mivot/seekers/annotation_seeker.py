# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Class with extraction tools for sub-block mapping
"""
from pyvo.mivot.utils.exceptions import MivotElementNotFound, MappingException
from pyvo.mivot.utils.vocabulary import Att, Ele
from pyvo.mivot import logger
from pyvo.mivot.utils.constant import Constant
from pyvo.utils.prototype import prototype_feature


@prototype_feature('MIVOT')
class AnnotationSeeker(object):
    """
    This class provides tools for extracting mapping sub-blocks commonly used by other stakeholders.
    All functions using the mapping employ this class to obtain XML elements.
    To simplify the job for other tools, the XML namespace is removed from the mapping block.

    Attributes
    ----------
    _xml_block : ~lxml.etree._Element
        Full mapping block.
    _globals_block : ~lxml.etree._Element or None
        GLOBALS block.
    _templates_blocks : dict
        Templates dictionary where keys are tableref and values are XML-TEMPLATES.
    """

    def __init__(self, xml_block):
        """
        Initializes the AnnotationSeeker.
        - Split the mapping as elements of interest.
        - Remove the name_spaces.
        - Append numbers to JOIN/REFERENCE.

        Parameters
        ----------
        xml_block : ~lxml.etree._Element
            XML mapping block.
        """
        self._xml_block = xml_block
        self._globals_block = None
        self._templates_blocks = {}

        self._find_globals_block()
        self._find_templates_blocks()
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
        This method iterates through the children of the XML mapping block, identifies TEMPLATES blocks,
        and associates them with their respective tableref values in the _templates_blocks dictionary.

        Returns
        -------
        dict
            Dictionary of TEMPLATES tablerefs and their mapping blocks
            Format: {'tableref': mapping_block, ...}

        Raises
        ------
        MivotElementNotFound
        If a TEMPLATES block is found without a tableref attribute, and there are already other TEMPLATES blocks.
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
        The elements that are renamed are:
        - JOIN
        - REFERENCE
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

        Parameters
        ----------
        name: str
            Name to compare
        expected: str
            Expected name for the comparison

        Returns
        -------
        bool
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
        Returns a list of all GLOBALS/COLLECTION elements.
        These collections have no dmroles but often dmids.
        They have particular roles
        - Used by references (e.g., filter definition)
        - Used as head of the mapped model (e.g., [Cube instance])

        Returns
        -------
        list
            List of GLOBALS/COLLECTION elements
        """
        return self._globals_block.xpath("//GLOBALS/COLLECTION")

    @property
    def models(self):
        """
        Gets the MODELs and their URLs.

        Returns
        -------
        dict
            Dictionary of MODELs and their URLs
            Format: {'model': [url], ...}
        """
        retour = {}
        eset = self._xml_block.xpath("//"+Ele.MODEL)
        for ele in eset:
            retour[ele.get("name")] = ele.get("url")
        return retour

    @property
    def templates_tableref(self):
        """
        Get all @tableref of the mapping.

        Returns
        -------
        list
            List of @tableref found in the mapping
        """
        return self._templates_blocks.keys()

    @property
    def templates(self):
        """
        Return a list of TEMPLATES tablerefs

        Returns
        -------
        list
            List of TEMPLATES tablerefs
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
        Return the TEMPLATES mapping block of the table matching @tableref.
        If tableref is None returns all values of templates_blocks.

        Parameters
        ----------
        tableref: str
            @tableref of the searched TEMPLATES

        Returns
        -------
        dict
            Dictionary of TEMPLATES tablerefs and their mapping blocks
            Format: {'tableref': mapping_block, ...}
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

        Returns
        -------
        dict
            Dict of @dmtypes of all mapped instances
            Format: {GLOBALS: [], TEMPLATES: {}}
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
        Parameters
        ----------
        dmtype_pattern: str
            @dmtype looked for

        Returns
        -------
        dict
            Dict of @dmtypes of all mapped instances
            Format: {'dmtype': [instance], ...}
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

        Returns
        -------
        list
            List of GLOBALS/INSTANCE elements
        """
        return self._globals_block.xpath("//"+Ele.GLOBALS+"/"+Ele.INSTANCE)

    def get_globals_instance_dmids(self):
        """
        Gets a list of @dmid for GLOBALS/INSTANCE

        Returns
        -------
        list
            List of @dmid of GLOBALS/INSTANCE
        """
        retour = []
        eset = self._globals_block.xpath("//"+Ele.INSTANCE+"[@"+Att.dmid+"]")
        for ele in eset:
            retour.append(ele.get(Att.dmid))
        return retour

    def get_globals_instance_by_dmid(self, dmid):
        """
        Gets the GLOBALS/INSTANCE with @dmid=dmid

        Parameters
        ----------
        dmid: str
            @dmid of the searched GLOBALS/INSTANCE

        Returns
        -------
        dict: `~lxml.etree._Element`
        """
        eset = self._globals_block.xpath("//"+Ele.INSTANCE+"[@"+Att.dmid+"='" + dmid + "']")
        for ele in eset:
            return ele
        return None

    def get_globals_instance_dmtypes(self):
        """
        Gets the list the @dmtype GLOBALS/INSTANCE

        Returns
        -------
        list
            List of @dmtype of GLOBALS/INSTANCE
        """
        retour = []
        for inst in self.get_globals_instances():
            retour.append(inst.get(Att.dmtype))
        return retour

    def get_templates_instance_by_dmid(self, tableref, dmid):
        """
        Gets the TEMPLATES/INSTANCE with @dmid=dmid and TEMPLATES@tableref=tableref

        Parameters
        ----------
        tableref: str
            @tableref of the searched TEMPLATES
        dmid: str
            @dmid of the searched TEMPLATES/INSTANCE

        Returns
        -------
        dict: `~lxml.etree._Element`
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

        Parameters
        ----------
        sourceref: str
            @dmid of the searched GLOBALS/COLLECTION
        pk_value: str
            @value of the searched GLOBALS/COLLECTION/INSTANCE/PRIMARY_KEY

        Returns
        -------
        dict: `~lxml.etree._Element`
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

        Parameters
        ----------
        dmid: str
            @dmid of the searched GLOBALS/COLLECTION

        Returns
        -------
        dict: `~lxml.etree._Element`
        """
        eset = self._globals_block.xpath("//"+Ele.GLOBALS+"/"+Ele.COLLECTION+"[@"+Att.dmid+"='" + dmid + "']")
        for ele in eset:
            return ele
        return None

    def get_globals_collection_dmids(self):
        """
        Gets the list of all the @dmid of GLOBALS/COLLECTION

        Returns
        -------
        list
            List of @dmid of GLOBALS/COLLECTION
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

        Returns
        -------
        list
            List of @dmtype of GLOBALS/COLLECTION/INSTANCE
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
        INSTANCE with a PRIMARY_key which @value matches key_value.
        An exception is risen if there is less or more than one element matching the criteria.
        The 2 parameters match the dynamic REFERENCE definition.

        Parameters
        ----------
        coll_dmid: str
            @dmid of the searched GLOBALS/COLLECTION
        key_value: str
            @value of the searched GLOBALS/COLLECTION/INSTANCE/PRIMARY_KEY

        Returns
        -------
        dict: `~lxml.etree._Element`

        Raises
        ------
        MivotElementNotFound
            If no element matches the criteria.
        MappingException
            If more than one element matches the criteria.
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
