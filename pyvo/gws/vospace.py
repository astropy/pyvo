# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
A module for interacting with a VOSpace service.

VOSpace is the IVOA interface to distributed storage. It specifies how
applications can use network attached data stores to persist and exchange
data in a standard way.

"""

import logging
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
from datetime import datetime
from collections import Counter
from requests import HTTPError

from ..utils.http import use_session
from ..utils.consts import IVOA_DATETIME_FORMAT

__all__ = ['VOSpaceService', 'ContainerNode']

from pyvo.dal.vosi import CapabilityMixin

VOSPACE_STANDARD_ID = 'ivo://ivoa.net/std/VOSpace/V2.0'

VOS_PROPERTIES = 'ivo://ivoa.net/std/VOSpace/v2.0#properties'  # The properties employed in the space.
VOS_VIEWS = 'ivo://ivoa.net/std/VOSpace/v2.0#views'  # The protocols employed in the space.
VOS_PROTOCOLS = 'ivo://ivoa.net/std/VOSpace/v2.0#protocols'  # The views employed in the space.
VOS_NODES = 'ivo://ivoa.net/std/VOSpace/v2.0#nodes'  # A Node under the nodes of the space.
VOS_TRANSFERS = 'ivo://ivoa.net/std/VOSpace/v2.0#transfers'  # Asynchronous transfers for the space.

VOS_SYNC_20 = 'ivo://ivoa.net/std/VOSpace/v2.0#sync'
VOS_SYNC_21 = 'ivo://ivoa.net/std/VOSpace#sync-2.1'


class VOSpaceService(CapabilityMixin):
    """
    a representation of a VOSpace service
    """

    def __init__(self, baseurl, *, capability_description=None, session=None):
        """
        instantiate a VOSpace service

        Parameters
        ----------
        url : str
           url - URL of the VOSpace service (base or nodes endpoint)
        session : object
           optional session to use for network requests
        """
        self.baseurl = baseurl.strip('/')
        if self.baseurl.endswith('nodes'):
            self.baseurl = self.baseurl[:-6]
        self.baseurl = baseurl
        self._session = use_session(session)

        # Check if the session has an update_from_capabilities attribute.
        # This means that the session is aware of IVOA capabilities,
        # and can use this information in processing network requests.
        # One such usecase for this is auth.
        if hasattr(self._session, 'update_from_capabilities'):
            self._session.update_from_capabilities(self.capabilities)

    def get_node(self, path, with_children=False):
        """
        Returns the node located in the path
        :param path: path of the node to return
        :param with_children: True to return the children if the node is a
        ContainerNode, False otherwise. It has no effect on other types of nodes
        :return: node
        :throws: NotFoundException
        """
        params = {}
        if not with_children:
            params = {'limit': 0}
        node_url = '{}/nodes/{}'.format(self.baseurl, path)
        response = self._session.get(node_url, params=params)
        response.raise_for_status()
        return ReaderWriter.from_xml(response.content)  # TODO stream response?

    def find_node(self, path):
        """
        Similar to get_node except that it returns the entire tree of a
        ContainerNode.

        Note: The tree is stored in memory, but a version with stream argument
        that allow caller to iterate through the nodes without loading them in
        memory first should be possible. This would probably be useful for
        a vfind command for ex.

        :param path: node path
        :return: node
        """
        root = self.get_node(path.strip('/'), with_children=True)
        if not isinstance(root, ContainerNode):
            return root
        self._resolve_containers(root)
        return root

    def _resolve_containers(self, container_node):
        for name in container_node._children.keys():
            node = container_node._children[name]
            node_path = '{}/{}'.format(container_node.path, node.name)
            if isinstance(node, ContainerNode):
                try:
                    node = self.get_node(node_path, with_children=True)
                    container_node._children[name] = node
                except HTTPError as e:
                    logging.debug('Cannot retrieve {}'.format(node_path), e)
                else:
                    self._resolve_containers(node)


class Node:
    """
        Represents a VOSpace node.
    """

    # xml elements
    # namespaces
    VOSNS = 'http://www.ivoa.net/xml/VOSpace/v2.0'
    XSINS = 'http://www.w3.org/2001/XMLSchema-instance'
    # node elements
    XML_TYPE = '{{{}}}type'.format(XSINS)
    XML_NODES = '{{{}}}nodes'.format(VOSNS)
    XML_NODE = '{{{}}}node'.format(VOSNS)
    XML_PROTOCOL = '{{{}}}protocol'.format(VOSNS)
    XML_PROPERTIES = '{{{}}}properties'.format(VOSNS)
    XML_PROPERTY = '{{{}}}property'.format(VOSNS)
    XML_ACCEPTS = '{{{}}}accepts'.format(VOSNS)
    XML_PROVIDES = '{{{}}}provides'.format(VOSNS)
    XML_ENDPOINT = '{{{}}}endpoint'.format(VOSNS)
    XML_TARGET = '{{{}}}target'.format(VOSNS)
    XML_BUSY = '{{{}}}busy'.format(VOSNS)
    XML_DATA_NODE_TYPE = 'vos:DataNode'
    XML_LINK_NODE_TYPE = 'vos:LinkNode'
    XML_CONTAINER_NODE_TYPE = 'vos:ContainerNode'

    # node properties
    NODE_PROP_CREATOR = 'ivo://ivoa.net/vospace/core#creator'
    NODE_PROP_DATE = 'ivo://ivoa.net/vospace/core#date'
    NODE_PROP_GROUPREAD = 'ivo://ivoa.net/vospace/core#groupread'
    NODE_PROP_GROUPWRITE = 'ivo://ivoa.net/vospace/core#groupwrite'
    NODE_PROP_PUBLICREAD = 'ivo://ivoa.net/vospace/core#ispublic'
    NODE_PROP_LENGTH = 'ivo://ivoa.net/vospace/core#length'

    def __init__(self, path):
        self._path = path.strip('/')
        self._owner = None
        self._is_public = False
        self._ro_groups = []
        self._wr_groups = []
        self._properties = {}
        self._last_mod = None
        self._length = None

    @property
    def path(self):
        return self._path

    @property
    def name(self):
        return self._path.split('/')[-1]

    @property
    def owner(self):
        return self._owner

    @owner.setter
    def owner(self, owner):
        self._owner = owner

    @property
    def is_public(self):
        return self._is_public

    @is_public.setter
    def is_public(self, is_public):
        self._is_public = is_public

    @property
    def ro_groups(self):
        return self._ro_groups

    @property
    def wr_groups(self):
        return self._wr_groups

    @property
    def properties(self):
        return self._properties

    @property
    def last_mod(self):
        return self._last_mod

    def __eq__(self, other):
        if not isinstance(other, Node):
            logging.debug('Expected node type for ' + other.path)
            return False
        result = ((self.path == other.path) and (self._owner == other.owner)
                  and (self.is_public == other.is_public) and (self.last_mod == other.last_mod)
                  and (Counter(self.ro_groups) == Counter(other.ro_groups))
                  and (Counter(self.wr_groups) == Counter(other.wr_groups))
                  and (Counter(self.properties) == Counter(other.properties)))
        if not result:
            logging.debug('Node attribute mismatch for ' + other.path)
        return result

    def _key(self):
        """
        Key used for the hash function.
        :return: key tuple
        """
        return (self.name)

    def __hash__(self):
        return hash(self._key())

    def __str__(self):
        return self.path + "(" + type(self).__name__ + ")"

    class NodeProperty:
        def __init__(self, id, value, readonly):
            self._id = id
            self.value = value
            self._readonly = readonly

        @property
        def id(self):
            return self._id

        @property
        def value(self):
            return self._value

        @value.setter
        def value(self, value):
            self._value = value

        @property
        def readonly(self):
            return self._readonly

        def __eq__(self, other):
            if not isinstance(other, Node.NodeProperty):
                logging.debug('Expected NodeProperty type for ' + other.path)
                return False
            result = ((self.id == other.id) and (self.value == other.value)
                    and (self.readonly == other.readonly))
            if not result:
                logging.debug('Property ' + self.id + ' mismatch')
            return result


class ReaderWriter:
    @staticmethod
    def from_xml(source):
        ET.register_namespace('xsi', Node.VOSNS)
        ET.register_namespace('vos', Node.XSINS)
        node_elem = ET.fromstring(source)
        return ReaderWriter._read_node(node_elem)

    @staticmethod
    def _read_node(node_elem):
        uri = node_elem.get('uri')
        path = urlparse(uri).path
        node_type = node_elem.get(Node.XML_TYPE)
        if node_type == Node.XML_CONTAINER_NODE_TYPE:
            node = ContainerNode(path)
            nodes_elem = node_elem.find(Node.XML_NODES)
            if nodes_elem:
                for child_elem in nodes_elem.findall(Node.XML_NODE):
                    node.add(ReaderWriter._read_node(child_elem))
        elif node_type == Node.XML_DATA_NODE_TYPE:
            busy = node_elem.get(Node.XML_BUSY)
            node = DataNode(path, busy=busy)
        elif node_type == Node.XML_LINK_NODE_TYPE:
            target = node_elem.find(Node.XML_TARGET)
            node = LinkNode(path, target.text)
        properties_elem = node_elem.find(Node.XML_PROPERTIES)
        if properties_elem:
            property_mapping = {
                Node.NODE_PROP_LENGTH: lambda: setattr(node, '_length', int(val)),
                Node.NODE_PROP_PUBLICREAD: lambda: setattr(node, 'is_public', val.lower() == 'true'),
                Node.NODE_PROP_CREATOR: lambda: setattr(node, 'owner', val),
                Node.NODE_PROP_DATE: lambda: setattr(node, '_last_mod',
                                                     datetime.strptime(val, IVOA_DATETIME_FORMAT)),
                Node.NODE_PROP_GROUPREAD: lambda: node.ro_groups.extend(
                    group_uri for group_uri in val.split(' ') if group_uri),
                Node.NODE_PROP_GROUPWRITE: lambda: node.wr_groups.extend(
                    group_uri for group_uri in val.split(' ') if group_uri),
            }
            for prop_elem in properties_elem.findall(Node.XML_PROPERTY):
                id = prop_elem.get('uri')
                val = prop_elem.text.strip()
                readonly = ((prop_elem.get('readonly') is not None)
                            and (prop_elem.get('readonly').lower() == 'true'))
                property_mapping.get(id, lambda: node.properties.update(
                    {id: Node.NodeProperty(id, val, readonly)}))()

        return node


class ContainerNode(Node):
    """
        Represents and container node
    """
    def __init__(self, path):
        super().__init__(path)
        self._children = {}

    def list_children(self):
        """
        return a list of children nodes
        :return:
        """
        return list(self._children.values())

    def add(self, child):
        if child.name in self._children.keys():
            raise ValueError("Duplicate node: " + str(child))
        self._children[child.name] = child

    def remove(self, child_name):
        try:
            del self._children[child_name.strip('/')]
        except KeyError:
            raise AttributeError("Not found: " + child_name)

    def __eq__(self, other):
        if not isinstance(other, ContainerNode):
            logging.debug('Expected ContainerNode type for ' + other.path)
            return False
        if len(self._children) != len(other._children):
            logging.debug('Mismatched number of children ' + self.path)
            return False
        for child in self._children.keys():
            try:
                if self._children[child] != other._children[child]:
                    logging.debug('Child mismatch ' + self._children[child].path)
                    return False
            except KeyError as e:
                logging.debug('Key error ' + str(e))
                return False
        return super().__eq__(other)

    def __hash__(self):
        return super().__hash__()

    def __str__(self):
        return super().__str__()


class DataNode(Node):
    """
        Represents a data node
    """

    def __init__(self, path, *, busy=None):
        super().__init__(path)
        self._content_checksum = None
        self._content_type = None
        self._busy = busy

    @property
    def busy(self):
        return self._busy

    @property
    def length(self):
        return self._length

    @property
    def content_checksum(self):
        return self._content_checksum

    @property
    def content_type(self):
        return self._content_type

    def __eq__(self, other):
        if not isinstance(other, DataNode):
            print('Not a DataNode ' + other.path)
            return False
        result = ((self.length == other.length) and (self.content_checksum == other.content_checksum)
                  and (self.content_type == other.content_type) and (self.busy == other.busy)
                  and super().__eq__(other))
        if not result:
            print('Mismatch data props in ' + self.path)
        return result

    def __hash__(self):
        return super().__hash__()

    def __str__(self):
        return super().__str__()


class LinkNode(Node):
    """
        Represents a link node
    """
    def __init__(self, path, target):
        super().__init__(path)
        self._target = target

    @property
    def target(self):
        return self._target

    def __eq__(self, other):
        if not isinstance(other, LinkNode):
            print('Not a LinkNode ' + other.path)
            return False

        result = (self.target == other.target) and super().__eq__(other)
        if not result:
            print('Mismatch target in ' + self.path)
        return result

    def __hash__(self):
        return super().__hash__()

    def __str__(self):
        return super().__str__()
