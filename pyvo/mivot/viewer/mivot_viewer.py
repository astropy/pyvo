# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
MivotViewer implements the user API for accessing mapped data.
- extracts the annotation block from the VOTable
- builds an XML view of the mapped model
- updates the leaves of the XML view with the values read in the data rows
- builds Python instances providing access to the mapped values by object attributes.

The code below shows a typical use of `MivotViewer

    .. code-block:: python

    with MivotViewer(path_to_votable) as mivot_viewer:
        print(f"mapped class id {mivot_instance.dmtype}")
        print(f"space frame is  {mivot_instance.Coordinate_coordSys.spaceRefFrame.value}")

        mivot_object = mivot_viewer.dm_instance
        while mivot_viewer.next_row_view():
            print(f"latitude={mivot_object.latitude.value}")
            print(f"longitude={mivot_object.longitude.value}")

See `tests/test_user_api.py`to get different examples of the API usage.
"""
import logging
from copy import deepcopy
from astropy import version
from astropy.io.votable import parse
from astropy.io.votable.tree import VOTableFile
from pyvo.dal import DALResults
from pyvo.mivot.utils.vocabulary import Ele, Att
from pyvo.mivot.utils.vocabulary import Constant, NoMapping
from pyvo.mivot.utils.exceptions import (MappingError,
                                         MivotError,
                                         AstropyVersionException)
from pyvo.mivot.utils.xml_utils import XmlUtils
from pyvo.mivot.utils.xpath_utils import XPath
from pyvo.mivot.seekers.annotation_seeker import AnnotationSeeker
from pyvo.mivot.seekers.resource_seeker import ResourceSeeker
from pyvo.mivot.seekers.table_iterator import TableIterator
from pyvo.mivot.features.static_reference_resolver import StaticReferenceResolver
from pyvo.mivot.version_checker import check_astropy_version
from pyvo.mivot.viewer.mivot_instance import MivotInstance
from pyvo.utils.prototype import prototype_feature
from pyvo.mivot.utils.mivot_utils import MivotUtils
# Use defusedxml only if already present in order to avoid a new depency.
try:
    from defusedxml import ElementTree as etree
except ImportError:
    from xml.etree import ElementTree as etree


@prototype_feature('MIVOT')
class MivotViewer:
    """
    MivotViewer is a PyVO table wrapper aiming at providing
    a model view on VOTable data read with usual tools.
    """
    def __init__(self, votable_path, tableref=None, resolve_ref=False):
        """
        Constructor of the MivotViewer class.

        Parameters
        ----------
        votable_path : str, DALResults, VOTableFile
            Reference of the VOTable from which Astropy will extracts the annotation block
        tableref : str, optional
            Used to identify the table to process. If not specified,
            the first table is taken by default.
        resolve_ref : boolean
            Ask for references between MIVOT instances to be resolved (referenced instances
            are copied into the host object). This is usually used to copy the coordinates
            systems into the object that uses them.
        Parameters
        ----------
        resolve_ref : bool, optional
            If True, replace the REFERENCE elements with a copy of the objects they refer to.
            e.g. copy the space coordinates system, usually located in the GLOBALS
            block, in the position objects
            Default is False.
        """
        if not check_astropy_version():
            raise AstropyVersionException(f"Astropy version {version.version} "
                                          f"is below the required version 6.0 for the use of MIVOT.")

        if isinstance(votable_path, DALResults):
            self._parsed_votable = votable_path.votable
        elif isinstance(votable_path, VOTableFile):
            self._parsed_votable = votable_path
        else:
            self._parsed_votable = parse(votable_path)
        self._table_iterator = None
        self._connected_table = None
        self._connected_tableref = None
        self._current_data_row = None
        # when the search object is in GLOBALS
        self._globals_instance = None
        self._last_row = None
        self._templates = None
        self._resource = None
        self._annotation_seeker = None
        self._mapping_block = None
        self._mapped_tables = []
        self._resource_seeker = None
        self._dm_instances = []
        self._dm_globals_instances = []
        self._resolve_ref = resolve_ref
        try:
            self._set_resource()
            self._set_mapping_block()
            self._resource_seeker = ResourceSeeker(self._resource)
            self._set_mapped_tables()
            self._connect_table(tableref)
            self._init_instances()
            self._init_globals_instances()
        except MappingError as mnf:
            logging.error(str(mnf))

    def __enter__(self):
        """ with statement implementation """
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """ with statement implementation """
        logging.info("MivotViewer closing..")

    def close(self):
        """ with statement implementation """
        logging.info("MivotViewer is closed")

    @property
    def votable(self):
        """
        returns the Astropy parsed votable
        """
        return self._parsed_votable

    @property
    def annotation_seeker(self):
        """
        Return an API to search various components in the XML mapping block.
        """
        return self._annotation_seeker

    @property
    def resource_seeker(self):
        """
        Return an API to search various components in the VOTabel resource.
        """
        return self._resource_seeker

    @property
    def connected_table(self):
        """
        getter for the identifier the astropy.table
        instance the viewer is connected to
        """
        return self._connected_table

    @property
    def connected_table_ref(self):
        """ getter for the identifier the table the viewer is connected to """
        return self._connected_tableref

    @property
    def dm_instance(self):
        """
        returns
        -------
            MivotInstance: The Python object (MivotInstance) built from the XML view of the
                           first 'TEMPLATES' child, with the attribute values set according
                           to the values of the current read data row.
        """
        dm_instances = self._dm_instances
        return self.dm_instances[0] if dm_instances else None

    @property
    def dm_instances(self):
        """
        Returns
        -------
           [MivotInstance]: The list of Python objects (MivotInstance) built from the XML views of
                            the TEMPLATES children, whose attribute values are set from the values
                            of the current read data row.
        """
        return self._dm_instances

    @property
    def dm_globals_instances(self):
        """
        Returns
        -------
           [MivotInstance]: The list of Python objects (MivotInstance) built from the XML views of
                            the GLOBALS children, whose attribute values are set from the values
                            of the current read data row.
                            This method allows to retrieve the GLOBALS (coordinates systems usually)
                            even when the viewer is in ``resolve_ref=False`` mode or if the reference
                            to the coordinates systems have not been setup in the objects representing
                            the mapped data.
        """
        return self._dm_globals_instances

    @property
    def table_row(self):
        """ getter for the current astropy.table.array row """
        return self._current_data_row

    def next_row_view(self):
        """
        jump to the next table row and update the MivotInstance instance with the row values

        Returns
        -------
        [MivotInstance]
            List of updated instances or None
            it he able end has been reached
        """
        self.next_table_row()

        if self._current_data_row is None:
            return None
        self._init_instances()

        for dm_instance in self._dm_instances:
            dm_instance.update(self._current_data_row)
        return self._dm_instances

    def get_table_ids(self):
        """
        Return a list of the table located just below self._resource.
        """
        if self.resource_seeker is None:
            return None
        return self.resource_seeker.get_table_ids()

    def get_models(self):
        """
        Get a dictionary of models and their URLs.

        Returns
        -------
        dict: Model names and a lists of their URLs.
              The format is {'model': [url], ...}.
        """
        if self._annotation_seeker is None:
            return None
        return self._annotation_seeker.get_models()

    def next_table_row(self):
        """
        Iterate once on the table row

        Returns:
             numpy row: the current table row of None if the end of the table has been reached
        """
        if self._table_iterator is None:
            return None
        self._current_data_row = self._table_iterator.get_next_row()
        return self._current_data_row

    def rewind(self):
        """
        Rewind the table iterator on the table the veizer is connected with.
        """
        if self._table_iterator:
            self._table_iterator.rewind()

    def _get_templates_child_instances(self, tableref=None):
        """
        Returns
        -------
        [`xml.etree.ElementTree.Element`]
            List of all INSTANCES elements children of the current TEMPLATES block
        """
        if self._annotation_seeker is None:
            return None
        templates_block = self._annotation_seeker.get_templates_block(tableref)
        return XPath.x_path(templates_block, ".//" + Ele.INSTANCE)

    def get_dm_instance_dmtypes(self, tableref):
        """
        Return the dmtypes of the INSTANCEs children of the
        TEMPLATES block mapping the data table identified by tableref.

        Parameters
        ----------
        tableref : str or None
            Identifier of the data table.

        Returns
        -------
        [string]
            list of dmtypes

        Raises
        ------
        MivotError
            if no INSTANCE can be found
        """
        dmtypes = []
        templates_block = self._annotation_seeker.get_templates_block(tableref)
        instances = XPath.x_path(templates_block, ".//" + Ele.INSTANCE)
        for instance in instances:
            dmtypes.append(instance.get(Att.dmtype))

        if not dmtypes:
            raise MivotError("Can't find " + Ele.INSTANCE + " in " + Ele.TEMPLATES)
        return dmtypes

    def _connect_table(self, tableref=None):
        """
        Iterate over the table identified by tableref.
        Required to browse table data.
        Connect to the first table if tableref is None.

        Parameters
        ----------
        tableref : str or None, optional
            Identifier of the table. If None, connects to the first table.
        """
        if not self._resource_seeker:
            raise MappingError("No mapping block found")

        stableref = tableref
        if tableref is None:
            stableref = ""
            self._connected_tableref = Constant.FIRST_TABLE
            logging.debug("Since " + Ele.TEMPLATES + "@table_ref is None, "
                         "the mapping will be applied to the first table."
                         )
        elif tableref not in self._mapped_tables:
            raise MappingError(f"The table {self._connected_tableref} doesn't match with any "
                                   f"mapped_table ({self._mapped_tables}) encountered in "
                                   + Ele.TEMPLATES
                                   )
        else:
            self._connected_tableref = tableref

        self._connected_table = self._resource_seeker.get_table(tableref)
        if self.connected_table is None:
            raise MivotError(f"Cannot find table {stableref} in VOTable")
        logging.debug("table %s found in VOTable", stableref)
        self._templates = deepcopy(self.annotation_seeker.get_templates_block(tableref))
        if self._templates is None:
            raise MivotError("Cannot find " + Ele.TEMPLATES + f" {stableref} ")
        logging.debug(Ele.TEMPLATES + " %s found ", stableref)
        self._table_iterator = TableIterator(self._connected_tableref,
                                             self.connected_table.to_table())
        self._squash_join_and_references()
        self._set_column_indices()
        self._set_column_units()

    def _get_model_view(self, xml_instance):
        """
        Return an XML model view of the last read row.

        - References are possibly resolved here.
        - ``ATTRIBUTE@value`` are set with actual data row values

        Returns
        -------
        `xml.etree.ElementTree.Element`
            XML model view  of the last read row.

        """
        templates_copy = deepcopy(xml_instance)
        if self._resolve_ref is True:
            while StaticReferenceResolver.resolve(self._annotation_seeker, self._connected_tableref,
                                                  templates_copy) > 0:
                pass
            # Make sure the instances of the resolved references
            # have both indexes and unit attribute
            XmlUtils.add_column_indices(templates_copy,
                                        self._resource_seeker
                                        .get_id_index_mapping(self._connected_tableref))
            XmlUtils.add_column_units(templates_copy,
                                      self._resource_seeker
                                      .get_id_unit_mapping(self._connected_tableref))
        for ele in XPath.x_path(templates_copy, ".//ATTRIBUTE"):
            ref = ele.get(Att.ref)
            if ref is not None and ref != Constant.NOT_SET and Constant.COL_INDEX in ele.attrib:
                index = ele.attrib[Constant.COL_INDEX]
                ele.attrib[Att.value] = str(self._current_data_row[int(index)])
        return templates_copy

    def _init_instances(self):
        """
        Read the first table row and build all MivotInstances (_dm_instances attribute) from it.
        The table row iterator in rewind at the end to make sure we won't lost the first data row.
        """
        if not self._dm_instances:
            self.next_table_row()
            xml_instances = self._get_templates_child_instances(self.connected_table_ref)
            self._dm_instances = []
            for xml_instance in xml_instances:
                self._dm_instances.append(
                    MivotInstance(
                        **MivotUtils.xml_to_dict(self._get_model_view(xml_instance))
                    ))
            self.rewind()

    def _init_globals_instances(self):
        """
        Build one MivotInstance for each GLOBALS/INSTANCE. Internal references are always resolved
        Globals MivotInstance are stored in the _dm_globals_instances list
        """
        if not self._dm_globals_instances:
            globals_copy = deepcopy(self._annotation_seeker.globals_block)

            while StaticReferenceResolver.resolve(self._annotation_seeker, None,
                                                  globals_copy) > 0:
                pass
            for ele in XPath.x_path(globals_copy, "./" + Ele.INSTANCE):
                self._dm_globals_instances.append(
                    MivotInstance(
                        **MivotUtils.xml_to_dict(ele)
                    ))

    def _set_mapped_tables(self):
        """
        Set the _mapped_tables list with the TEMPLATES tablerefs.
        """
        if not self.resource_seeker:
            self._mapped_tables = []
        else:
            self._mapped_tables = self._annotation_seeker.get_templates()

    def _set_resource(self):
        """
        select the first resource with @type=results
        The annotations, if there are, are supposed to be there.
        The case of multiple 'results' annotated is not taken into account yest
        """

        if len(self._parsed_votable.resources) < 1:
            raise MivotError("No resource detected in the VOTable")
        rnb = 0
        for res in self._parsed_votable.resources:
            if res.type.lower() == "results":
                logging.info("Resource %s selected", rnb)
                self._resource = self._parsed_votable.resources[rnb]
                return
            rnb += 1
        raise MivotError("No resource @type='results'detected in the VOTable")

    def _set_mapping_block(self):
        """
        Set the mapping block found in the resource and set the annotation_seeker
        """
        if NoMapping.search(self._resource.mivot_block.content):
            raise MappingError("Mivot block is not found")
        # The namespace should be removed
        self._mapping_block = (
            etree.fromstring(self._resource.mivot_block.content
                            .replace('xmlns="http://www.ivoa.net/xml/mivot"', '')
                            .replace("xmlns='http://www.ivoa.net/xml/mivot'", '')))
        self._annotation_seeker = AnnotationSeeker(self._mapping_block)
        logging.info("Mapping block found")

    def _squash_join_and_references(self):
        """
        Remove both JOINs and REFERENCEs from the templates
        and store them in to be resolved later on.
        This prevents the model view of being polluted with elements that are not in the model
        """
        for ele in XPath.x_path_startwith(self._templates, ".//REFERENCE_"):
            if ele.get("sourceref") is not None:
                self._dyn_references = {ele.tag: deepcopy(ele)}
                for child in list(ele):
                    ele.remove(child)
        for ele in XPath.x_path_startwith(self._templates, ".//JOIN_"):
            self._joins = {ele.tag: deepcopy(ele)}
            for child in list(ele):
                ele.remove(child)

    def _set_column_indices(self):
        """
        Add column ranks to attribute having a ref.
        Using ranks allow identifying columns even when numpy raw have been serialised as []
        """
        index_map = self._resource_seeker.get_id_index_mapping(self._connected_tableref)
        XmlUtils.add_column_indices(self._templates, index_map)

    def _set_column_units(self):
        """
        Add field unit to attribute having a ref.
        Used for performing unit conversions
        """
        unit_map = self._resource_seeker.get_id_unit_mapping(self._connected_tableref)
        XmlUtils.add_column_units(self._templates, unit_map)
